# Threat Intelligence Provider Tests

Comprehensive test suite for the External Threat Intelligence system.

## Test File

`test_external_threat_providers.py` - 31 tests covering all threat intelligence providers and agent logic.

## Test Coverage

### 1. CountryRiskProvider (4 tests - always pass, local)
- ✅ `test_blacklisted_country` - KP (North Korea) → confidence 1.0
- ✅ `test_graylist_country` - NG (Nigeria) → confidence 0.65-0.75
- ✅ `test_elevated_risk_country` - RU (Russia) → confidence 0.75
- ✅ `test_safe_country` - PE (Peru) → empty list

### 2. OSINTSearchProvider (5 tests - 4 mocked, 1 integration)
- ✅ `test_osint_search_disabled_via_config` - Config flag OFF → empty list
- ✅ `test_osint_search_with_mock_results` - Mocked DuckDuckGo → returns sources
- ✅ `test_osint_search_timeout` - Timeout → empty list (graceful)
- ✅ `test_osint_search_error_graceful` - Network error → empty list (graceful)
- 🌐 `test_osint_search_real_query` - **Integration** (requires internet)

### 3. SanctionsProvider (4 tests - 3 mocked, 1 integration)
- ✅ `test_sanctions_no_api_key` - No API key → empty list (silent skip)
- ✅ `test_sanctions_disabled_via_config` - Config flag OFF → empty list
- ✅ `test_sanctions_api_error_graceful` - API error → empty list (graceful)
- 🌐 `test_sanctions_with_real_api_key` - **Integration** (requires API key)

### 4. Baseline Calculation (4 tests)
- ✅ `test_calculate_baseline_empty_sources` - No sources → 0.0
- ✅ `test_calculate_baseline_single_source` - One source → its confidence
- ✅ `test_calculate_baseline_multi_source_bonus` - Multiple → max + 0.1 * (count - 1)
- ✅ `test_calculate_baseline_clamped_to_one` - High multi-source → clamped to 1.0

### 5. Provider Type Classification (4 tests)
- ✅ `test_classify_provider_type_fatf` - FATF sources → "FATF"
- ✅ `test_classify_provider_type_osint` - OSINT sources → "OSINT"
- ✅ `test_classify_provider_type_sanctions` - Sanctions sources → "Sanctions"
- ✅ `test_classify_provider_type_unknown` - Unknown sources → "Unknown"

### 6. Provider Management (3 tests)
- ✅ `test_get_enabled_providers_all_enabled` - All flags ON → 3 providers
- ✅ `test_get_enabled_providers_only_country_risk` - All flags OFF → 1 provider (CountryRisk)
- ✅ `test_get_enabled_providers_no_sanctions_without_key` - No API key → skip Sanctions

### 7. Parallel Execution (3 tests)
- ✅ `test_gather_threat_intel_parallel_execution` - Verify parallel execution (< 0.15s for 2x 0.1s tasks)
- ✅ `test_gather_threat_intel_one_provider_fails` - One failure doesn't block others
- ✅ `test_gather_threat_intel_timeout` - Timeout handling (15s per provider)

### 8. Agent End-to-End (4 tests - 3 mocked, 1 integration)
- ✅ `test_external_threat_agent_all_providers_fail` - All fail → threat_level 0.0
- ✅ `test_external_threat_agent_country_risk_only` - Only CountryRisk → works
- ✅ `test_external_threat_agent_with_signals` - Passes signals to providers
- 🌐 `test_external_threat_agent_full_integration` - **Integration** (requires internet)

## Running Tests

### Run All Unit Tests (Mocked APIs)
```bash
cd backend

# Run all unit tests (excludes integration tests)
uv run pytest tests/test_agents/test_external_threat_providers.py -v -m "not integration"

# Output: 28 passed, 3 deselected (integration) in ~16s
```

### Run Integration Tests (Real APIs)
```bash
# Run only integration tests (requires internet + optional API keys)
uv run pytest tests/test_agents/test_external_threat_providers.py -v -m "integration"

# Output: 3 tests (may skip if no API key)
```

### Run All Tests (Unit + Integration)
```bash
# Run everything
uv run pytest tests/test_agents/test_external_threat_providers.py -v

# Output: 31 total tests
```

### Run Specific Test
```bash
# Run single test
uv run pytest tests/test_agents/test_external_threat_providers.py::test_blacklisted_country -v

# Run all CountryRisk tests
uv run pytest tests/test_agents/test_external_threat_providers.py -v -k "country"
```

## Test Fixtures

### Transaction Fixtures
```python
transaction_high_risk
    # KP (blacklist), $50k, merchant M-999, unknown device

transaction_medium_risk
    # RU (elevated risk), $5k, merchant M-100

transaction_low_risk
    # PE (safe), $100, merchant M-001
```

### Signal Fixtures
```python
transaction_signals_high_risk
    # amount_ratio=50.0, off_hours=True, foreign=True, unknown_device=True

transaction_signals_low_risk
    # amount_ratio=1.0, all flags False
```

## Mocking Strategy

### External APIs Mocked
```python
# OSINT (DuckDuckGo)
with patch("app.services.threat_intel.osint_search.DDGS") as mock_ddgs:
    mock_ddgs.return_value.text.return_value = [...]

# Sanctions (OpenSanctions)
with patch("app.services.threat_intel.sanctions_screening.httpx.AsyncClient") as mock_client:
    mock_client.return_value.__aenter__.return_value.get.return_value = ...

# LLM (Ollama)
with patch("app.agents.external_threat.get_llm") as mock_get_llm:
    mock_llm.ainvoke.side_effect = Exception("LLM not available")
```

### Config Settings Mocked
```python
with patch("app.agents.external_threat.settings") as mock_settings:
    mock_settings.threat_intel_enable_osint = True
    mock_settings.opensanctions_api_key = "fake-key"
```

## Integration Test Requirements

### For OSINT Integration Tests
- ✅ Internet connection
- ✅ `THREAT_INTEL_ENABLE_OSINT=true` in `.env`

### For Sanctions Integration Tests
- ✅ Internet connection
- ✅ `OPENSANCTIONS_API_KEY=<your-key>` in `.env`
- ⚠️ Test will **skip** if no API key configured (not fail)

### For Full Agent Integration
- ✅ Internet connection
- ✅ FATF lists JSON file present (`data/fatf_lists.json`)
- ⚠️ LLM is mocked (Ollama not required)

## Test Performance

```
Unit Tests (mocked):     ~16s for 28 tests
Integration Tests:       ~20s for 3 tests (depends on network)
Total:                   ~36s for all 31 tests
```

## Expected Results

### Unit Tests (No Network Required)
```bash
$ uv run pytest tests/test_agents/test_external_threat_providers.py -v -m "not integration"

======================== 28 passed, 3 deselected in 16.33s ========================
```

### Integration Tests (Network Required)
```bash
$ uv run pytest tests/test_agents/test_external_threat_providers.py -v -m "integration"

======================== 3 passed in 20.12s ========================
# OR
======================== 2 passed, 1 skipped in 15.23s ========================
# (1 skipped if no OpenSanctions API key)
```

## Debugging Failed Tests

### View Full Traceback
```bash
uv run pytest tests/test_agents/test_external_threat_providers.py::test_name -vv --tb=long
```

### Print Test Output
```bash
uv run pytest tests/test_agents/test_external_threat_providers.py::test_name -s
```

### Run with Debugger
```bash
uv run pytest tests/test_agents/test_external_threat_providers.py::test_name --pdb
```

## Coverage Report (Optional)

```bash
# Run with coverage
uv run pytest tests/test_agents/test_external_threat_providers.py --cov=app.agents.external_threat --cov=app.services.threat_intel --cov-report=html

# View report
open htmlcov/index.html
```

## Common Issues

### 1. "ModuleNotFoundError: No module named 'app'"
**Solution**: Run tests from `backend/` directory, not from `tests/`

### 2. "FATF lists not found"
**Solution**: Ensure `backend/data/fatf_lists.json` exists

### 3. Integration tests timeout
**Solution**: Check internet connection, or skip with `-m "not integration"`

### 4. Mock not working
**Solution**: Verify patch path matches import path in source file

## CI/CD Integration

### pytest.ini Configuration
```ini
[pytest]
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
    slow: marks tests as slow (deselect with '-m "not slow"')

asyncio_mode = auto
```

### GitHub Actions Example
```yaml
- name: Run unit tests
  run: |
    cd backend
    uv run pytest tests/test_agents/test_external_threat_providers.py -v -m "not integration"
```

## Test Maintenance

### Adding New Provider Tests
1. Create fixture for provider instance
2. Test with mock data
3. Test error handling (graceful degradation)
4. Test config flags (enable/disable)
5. Add integration test (mark with `@pytest.mark.integration`)

### Adding New Agent Tests
1. Use existing fixtures (transaction_high_risk, etc.)
2. Mock LLM (get_llm)
3. Mock external providers if needed
4. Verify threat_level and sources

## Success Criteria

✅ All unit tests pass without network (28/28)
✅ All mocks properly isolate external dependencies
✅ Integration tests skip gracefully without API keys
✅ Parallel execution verified (timing tests)
✅ Graceful degradation tested (all failure modes)
✅ Baseline calculation validated (edge cases)
✅ Provider classification working correctly

---

**Last Updated**: 2026-02-14
**Test Count**: 31 (28 unit, 3 integration)
**Status**: ✅ All Passing
