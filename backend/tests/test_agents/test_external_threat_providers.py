"""Tests for External Threat Intelligence Providers and Refactored Agent.

Uses pytest + pytest-asyncio for async testing.
Mocks external APIs (DuckDuckGo, OpenSanctions) for unit tests.
Integration tests (marked with @pytest.mark.integration) make real API calls.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from app.agents.external_threat import (
    _gather_threat_intel,
    _get_enabled_providers,
    external_threat_agent,
)
from app.agents.threat_utils import (
    calculate_baseline_from_sources as _calculate_baseline_from_sources,
    classify_provider_type as _classify_provider_type,
)
from app.config import settings
from app.models import OrchestratorState, Transaction, TransactionSignals, ThreatSource
from app.services.threat_intel import (
    CountryRiskProvider,
    OSINTSearchProvider,
    SanctionsProvider,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def transaction_high_risk():
    """High-risk transaction: blacklist country + suspicious merchant."""
    return Transaction(
        transaction_id="TX-HIGH-001",
        customer_id="C-999",
        amount=50000,
        currency="USD",
        country="KP",  # North Korea - FATF blacklist
        channel="web",
        device_id="D-UNKNOWN",
        timestamp=datetime.now(UTC),
        merchant_id="M-999",
    )


@pytest.fixture
def transaction_medium_risk():
    """Medium-risk transaction: elevated risk country."""
    return Transaction(
        transaction_id="TX-MED-001",
        customer_id="C-100",
        amount=5000,
        currency="USD",
        country="RU",  # Russia - elevated risk
        channel="web",
        device_id="D-123",
        timestamp=datetime.now(UTC),
        merchant_id="M-100",
    )


@pytest.fixture
def transaction_low_risk():
    """Low-risk transaction: safe country + normal merchant."""
    return Transaction(
        transaction_id="TX-LOW-001",
        customer_id="C-001",
        amount=100,
        currency="PEN",
        country="PE",  # Peru - safe
        channel="web",
        device_id="D-001",
        timestamp=datetime.now(UTC),
        merchant_id="M-001",
    )


@pytest.fixture
def transaction_signals_high_risk():
    """High-risk transaction signals."""
    return TransactionSignals(
        amount_ratio=50.0,
        is_off_hours=True,
        is_foreign=True,
        is_unknown_device=True,
        channel_risk="high",
        flags=["very_high_amount", "blacklist_country", "unknown_device"],
    )


@pytest.fixture
def transaction_signals_low_risk():
    """Low-risk transaction signals."""
    return TransactionSignals(
        amount_ratio=1.0,
        is_off_hours=False,
        is_foreign=False,
        is_unknown_device=False,
        channel_risk="low",
        flags=[],
    )


# ============================================================================
# CountryRiskProvider Tests (Local, Always Pass)
# ============================================================================


@pytest.mark.asyncio
async def test_blacklisted_country(transaction_high_risk):
    """Blacklist country (KP) should return ThreatSource with score ~1.0."""
    provider = CountryRiskProvider()
    sources = await provider.lookup(transaction_high_risk)

    assert len(sources) == 1
    assert sources[0].source_name == "fatf_blacklist_KP"
    assert sources[0].confidence == 1.0


@pytest.mark.asyncio
async def test_graylist_country():
    """Graylist country (NG) should return ThreatSource with score ~0.65-0.75."""
    provider = CountryRiskProvider()

    transaction = Transaction(
        transaction_id="TX-GRAY-001",
        customer_id="C-001",
        amount=1000,
        currency="USD",
        country="NG",  # Nigeria - graylist
        channel="web",
        device_id="D-001",
        timestamp=datetime.now(UTC),
        merchant_id="M-001",
    )

    sources = await provider.lookup(transaction)

    assert len(sources) == 1
    assert sources[0].source_name == "fatf_graylist_NG"
    assert 0.65 <= sources[0].confidence <= 0.75


@pytest.mark.asyncio
async def test_elevated_risk_country(transaction_medium_risk):
    """Elevated risk country (RU) should return ThreatSource with score ~0.75."""
    provider = CountryRiskProvider()
    sources = await provider.lookup(transaction_medium_risk)

    assert len(sources) == 1
    assert sources[0].source_name == "elevated_risk_RU"
    assert sources[0].confidence == 0.75


@pytest.mark.asyncio
async def test_safe_country(transaction_low_risk):
    """Safe country (PE) should return empty list."""
    provider = CountryRiskProvider()
    sources = await provider.lookup(transaction_low_risk)

    assert len(sources) == 0


# ============================================================================
# OSINTSearchProvider Tests (Mocked + Integration)
# ============================================================================


@pytest.mark.asyncio
async def test_osint_search_disabled_via_config(transaction_high_risk):
    """OSINT search disabled via config should return empty list."""
    with patch("app.services.threat_intel.osint_search.settings") as mock_settings:
        mock_settings.threat_intel_enable_osint = False

        provider = OSINTSearchProvider()
        sources = await provider.lookup(transaction_high_risk)

        assert len(sources) == 0


@pytest.mark.asyncio
async def test_osint_search_with_mock_results(transaction_high_risk):
    """OSINT search with mocked results should return ThreatSource."""
    with patch("app.services.threat_intel.osint_search.DDGS") as mock_ddgs:
        # Mock DuckDuckGo to return fake results
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"title": "Fraud alert for M-999", "body": "Multiple fraud reports"},
            {"title": "Sanctions warning", "body": "High risk merchant"},
        ]

        provider = OSINTSearchProvider(max_results=2)
        sources = await provider.lookup(transaction_high_risk)

        # Should have at least one source (confidence >= 0.4)
        assert len(sources) >= 1
        assert all(s.source_name == "osint_web_search" for s in sources)
        assert all(0.4 <= s.confidence <= 1.0 for s in sources)


@pytest.mark.asyncio
async def test_osint_search_timeout(transaction_high_risk):
    """OSINT search timeout should return empty list gracefully."""
    with patch("app.services.threat_intel.osint_search.DDGS") as mock_ddgs:
        # Mock to raise timeout
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value = mock_ddgs_instance

        async def slow_search(*args, **kwargs):
            await asyncio.sleep(20)  # Exceeds 10s timeout
            return []

        provider = OSINTSearchProvider()

        # Patch the _search method to timeout
        with patch.object(provider, "_search", side_effect=asyncio.TimeoutError):
            sources = await provider.lookup(transaction_high_risk)

            # Should return empty list, not crash
            assert len(sources) == 0


@pytest.mark.asyncio
async def test_osint_search_error_graceful(transaction_high_risk):
    """OSINT search error should return empty list gracefully."""
    with patch("app.services.threat_intel.osint_search.DDGS") as mock_ddgs:
        # Mock to raise exception
        mock_ddgs.side_effect = Exception("Network error")

        provider = OSINTSearchProvider()
        sources = await provider.lookup(transaction_high_risk)

        # Should return empty list, not crash
        assert len(sources) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_osint_search_real_query(transaction_high_risk):
    """OSINT search with real query (integration test - requires internet)."""
    provider = OSINTSearchProvider(max_results=3)
    sources = await provider.lookup(transaction_high_risk)

    # May or may not find results, but should not crash
    assert isinstance(sources, list)
    # If sources found, validate structure
    for source in sources:
        assert source.source_name == "osint_web_search"
        assert 0.0 <= source.confidence <= 1.0


# ============================================================================
# SanctionsProvider Tests (Mocked + Integration)
# ============================================================================


@pytest.mark.asyncio
async def test_sanctions_no_api_key(transaction_high_risk):
    """Sanctions provider without API key should skip gracefully."""
    with patch("app.services.threat_intel.sanctions_screening.settings") as mock_settings:
        mock_settings.opensanctions_api_key = SecretStr("")

        provider = SanctionsProvider()
        sources = await provider.lookup(transaction_high_risk)

        # Should return empty list, not crash
        assert len(sources) == 0


@pytest.mark.asyncio
async def test_sanctions_disabled_via_config(transaction_high_risk):
    """Sanctions disabled via config should return empty list."""
    with patch("app.services.threat_intel.sanctions_screening.settings") as mock_settings:
        mock_settings.opensanctions_api_key = SecretStr("fake-key")
        mock_settings.threat_intel_enable_sanctions = False

        provider = SanctionsProvider()
        sources = await provider.lookup(transaction_high_risk)

        assert len(sources) == 0


@pytest.mark.asyncio
async def test_sanctions_api_error_graceful(transaction_high_risk):
    """Sanctions API error should return empty list gracefully."""
    with patch("app.services.threat_intel.sanctions_screening.httpx.AsyncClient") as mock_client:
        # Mock API to raise HTTP error
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.side_effect = Exception("API error")

        with patch("app.services.threat_intel.sanctions_screening.settings") as mock_settings:
            mock_settings.opensanctions_api_key = SecretStr("fake-key")
            mock_settings.threat_intel_enable_sanctions = True

            provider = SanctionsProvider()
            sources = await provider.lookup(transaction_high_risk)

            # Should return empty list, not crash
            assert len(sources) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sanctions_with_real_api_key(transaction_high_risk):
    """Sanctions with real API key (integration test - requires API key)."""
    # Skip if no API key configured
    if not settings.opensanctions_api_key.get_secret_value():
        pytest.skip("No OpenSanctions API key configured")

    provider = SanctionsProvider()
    sources = await provider.lookup(transaction_high_risk)

    # Should not crash, may or may not find matches
    assert isinstance(sources, list)


# ============================================================================
# Baseline Calculation Tests
# ============================================================================


def test_calculate_baseline_empty_sources():
    """Baseline with no sources should be 0.0."""
    baseline = _calculate_baseline_from_sources([])
    assert baseline == 0.0


def test_calculate_baseline_single_source():
    """Baseline with single source should be its confidence."""
    sources = [ThreatSource(source_name="test", confidence=0.75)]
    baseline = _calculate_baseline_from_sources(sources)
    assert baseline == 0.75


def test_calculate_baseline_multi_source_bonus():
    """Baseline with multiple sources should add 0.1 bonus per extra source."""
    sources = [
        ThreatSource(source_name="source1", confidence=0.8),
        ThreatSource(source_name="source2", confidence=0.5),
    ]
    baseline = _calculate_baseline_from_sources(sources)

    # max(0.8, 0.5) + 0.1 = 0.9
    assert baseline == 0.9


def test_calculate_baseline_clamped_to_one():
    """Baseline should be clamped to 1.0 maximum."""
    sources = [
        ThreatSource(source_name="source1", confidence=1.0),
        ThreatSource(source_name="source2", confidence=0.9),
        ThreatSource(source_name="source3", confidence=0.8),
    ]
    baseline = _calculate_baseline_from_sources(sources)

    # max(1.0, 0.9, 0.8) + 0.2 = 1.2, clamped to 1.0
    assert baseline == 1.0


# ============================================================================
# Provider Type Classification Tests
# ============================================================================


def test_classify_provider_type_fatf():
    """FATF sources should be classified as FATF."""
    assert _classify_provider_type("fatf_blacklist_KP") == "FATF"
    assert _classify_provider_type("fatf_graylist_NG") == "FATF"
    assert _classify_provider_type("elevated_risk_RU") == "FATF"


def test_classify_provider_type_osint():
    """OSINT sources should be classified as OSINT."""
    assert _classify_provider_type("osint_web_search") == "OSINT"


def test_classify_provider_type_sanctions():
    """Sanctions sources should be classified as Sanctions."""
    assert _classify_provider_type("opensanctions_Person") == "Sanctions"
    assert _classify_provider_type("sanctions_match") == "Sanctions"


def test_classify_provider_type_unknown():
    """Unknown sources should be classified as Unknown."""
    assert _classify_provider_type("random_provider") == "Unknown"


# ============================================================================
# Provider Management Tests
# ============================================================================


def test_get_enabled_providers_all_enabled():
    """All providers enabled should return 3 providers."""
    with patch("app.agents.external_threat.settings") as mock_settings:
        mock_settings.threat_intel_enable_osint = True
        mock_settings.threat_intel_enable_sanctions = True
        mock_settings.opensanctions_api_key = SecretStr("fake-key")
        mock_settings.threat_intel_osint_max_results = 5

        providers = _get_enabled_providers()

        assert len(providers) == 3
        assert isinstance(providers[0], CountryRiskProvider)
        assert isinstance(providers[1], OSINTSearchProvider)
        assert isinstance(providers[2], SanctionsProvider)


def test_get_enabled_providers_only_country_risk():
    """Only country risk enabled should return 1 provider."""
    with patch("app.agents.external_threat.settings") as mock_settings:
        mock_settings.threat_intel_enable_osint = False
        mock_settings.threat_intel_enable_sanctions = False

        providers = _get_enabled_providers()

        assert len(providers) == 1
        assert isinstance(providers[0], CountryRiskProvider)


def test_get_enabled_providers_no_sanctions_without_key():
    """Sanctions without API key should not be included."""
    with patch("app.agents.external_threat.settings") as mock_settings:
        mock_settings.threat_intel_enable_osint = True
        mock_settings.threat_intel_enable_sanctions = True
        mock_settings.opensanctions_api_key = SecretStr("")  # No key
        mock_settings.threat_intel_osint_max_results = 5

        providers = _get_enabled_providers()

        # Should have Country Risk + OSINT only (no Sanctions)
        assert len(providers) == 2
        assert isinstance(providers[0], CountryRiskProvider)
        assert isinstance(providers[1], OSINTSearchProvider)


# ============================================================================
# Parallel Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_gather_threat_intel_parallel_execution(transaction_high_risk):
    """Providers should execute in parallel."""
    # Create mock providers with delays
    async def mock_lookup_1(tx, sig):
        await asyncio.sleep(0.1)
        return [ThreatSource(source_name="mock1", confidence=0.5)]

    async def mock_lookup_2(tx, sig):
        await asyncio.sleep(0.1)
        return [ThreatSource(source_name="mock2", confidence=0.6)]

    mock_provider1 = AsyncMock()
    mock_provider1.provider_name = "mock1"
    mock_provider1.lookup = mock_lookup_1

    mock_provider2 = AsyncMock()
    mock_provider2.provider_name = "mock2"
    mock_provider2.lookup = mock_lookup_2

    providers = [mock_provider1, mock_provider2]

    # Measure execution time
    start = asyncio.get_event_loop().time()
    sources = await _gather_threat_intel(providers, transaction_high_risk, None)
    elapsed = asyncio.get_event_loop().time() - start

    # Should complete in ~0.1s (parallel), not 0.2s (sequential)
    assert elapsed < 0.15  # Some overhead allowed
    assert len(sources) == 2


@pytest.mark.asyncio
async def test_gather_threat_intel_one_provider_fails(transaction_high_risk):
    """One provider failing should not block others."""
    # Provider 1: succeeds
    mock_provider1 = AsyncMock()
    mock_provider1.provider_name = "mock1"
    mock_provider1.lookup = AsyncMock(
        return_value=[ThreatSource(source_name="mock1", confidence=0.5)]
    )

    # Provider 2: fails
    mock_provider2 = AsyncMock()
    mock_provider2.provider_name = "mock2"
    mock_provider2.lookup = AsyncMock(side_effect=Exception("Provider failed"))

    providers = [mock_provider1, mock_provider2]

    sources = await _gather_threat_intel(providers, transaction_high_risk, None)

    # Should have 1 source from successful provider
    assert len(sources) == 1
    assert sources[0].source_name == "mock1"


@pytest.mark.asyncio
async def test_gather_threat_intel_timeout(transaction_high_risk):
    """Provider timeout should not crash gather."""
    # Provider that times out
    mock_provider = AsyncMock()
    mock_provider.provider_name = "slow_provider"

    async def slow_lookup(*args, **kwargs):
        await asyncio.sleep(20)  # Exceeds 15s timeout
        return []

    mock_provider.lookup = slow_lookup

    providers = [mock_provider]

    # Should handle timeout gracefully
    sources = await _gather_threat_intel(providers, transaction_high_risk, None)

    # Should return empty (timeout caught)
    assert len(sources) == 0


# ============================================================================
# Refactored Agent End-to-End Tests
# ============================================================================


@pytest.mark.asyncio
async def test_external_threat_agent_all_providers_fail(transaction_low_risk):
    """Agent with all providers failing should return threat_level 0.0."""
    # Mock all providers to fail
    with patch("app.agents.external_threat._get_enabled_providers") as mock_get_providers:
        mock_provider = AsyncMock()
        mock_provider.provider_name = "failing_provider"
        mock_provider.lookup = AsyncMock(side_effect=Exception("All providers failed"))

        mock_get_providers.return_value = [mock_provider]

        state: OrchestratorState = {
            "transaction": transaction_low_risk,
            "transaction_signals": None,
            "behavior_analysis": None,
            "policy_matches": None,
            "threat_intel": None,
            "evidence": None,
            "debate_result": None,
            "decision": None,
            "explanations": None,
        }

        result = await external_threat_agent(state)

        assert result["threat_intel"].threat_level == 0.0
        assert len(result["threat_intel"].sources) == 0


@pytest.mark.asyncio
async def test_external_threat_agent_country_risk_only(transaction_high_risk):
    """Agent with only country risk enabled should work."""
    with patch("app.agents.external_threat.settings") as mock_settings:
        mock_settings.threat_intel_enable_osint = False
        mock_settings.threat_intel_enable_sanctions = False

        state: OrchestratorState = {
            "transaction": transaction_high_risk,
            "transaction_signals": None,
            "behavior_analysis": None,
            "policy_matches": None,
            "threat_intel": None,
            "evidence": None,
            "debate_result": None,
            "decision": None,
            "explanations": None,
        }

        # Mock LLM to avoid Ollama dependency
        with patch("app.agents.external_threat.get_llm") as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM not available"))
            mock_get_llm.return_value = mock_llm

            result = await external_threat_agent(state)

            # Should have threat from FATF blacklist
            assert result["threat_intel"].threat_level > 0.8
            assert len(result["threat_intel"].sources) >= 1


@pytest.mark.asyncio
async def test_external_threat_agent_with_signals(
    transaction_high_risk, transaction_signals_high_risk
):
    """Agent with transaction signals should pass them to providers."""
    state: OrchestratorState = {
        "transaction": transaction_high_risk,
        "transaction_signals": transaction_signals_high_risk,
        "behavior_analysis": None,
        "policy_matches": None,
        "threat_intel": None,
        "evidence": None,
        "debate_result": None,
        "decision": None,
        "explanations": None,
    }

    # Mock LLM to avoid Ollama dependency
    with patch("app.agents.external_threat.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM not available"))
        mock_get_llm.return_value = mock_llm

        # Mock OSINT to avoid real web search
        with patch("app.services.threat_intel.osint_search.DDGS") as mock_ddgs:
            mock_ddgs_instance = MagicMock()
            mock_ddgs.return_value = mock_ddgs_instance
            mock_ddgs_instance.text.return_value = []

            result = await external_threat_agent(state)

            # Should have sources from FATF at minimum
            assert result["threat_intel"].threat_level > 0.0
            assert len(result["threat_intel"].sources) >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_external_threat_agent_full_integration(
    transaction_medium_risk, transaction_signals_low_risk
):
    """Full integration test with real providers (requires internet)."""
    state: OrchestratorState = {
        "transaction": transaction_medium_risk,
        "transaction_signals": transaction_signals_low_risk,
        "behavior_analysis": None,
        "policy_matches": None,
        "threat_intel": None,
        "evidence": None,
        "debate_result": None,
        "decision": None,
        "explanations": None,
    }

    # Mock LLM only (let providers run real)
    with patch("app.agents.external_threat.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM not available"))
        mock_get_llm.return_value = mock_llm

        result = await external_threat_agent(state)

        # Should have elevated risk from Russia
        assert result["threat_intel"].threat_level > 0.0
        assert len(result["threat_intel"].sources) >= 1

        # Verify source names
        source_names = [s.source_name for s in result["threat_intel"].sources]
        assert any("elevated_risk" in name or "fatf" in name.lower() for name in source_names)
