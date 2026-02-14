# Threat Intelligence Provider Tests

Tests for the modular threat intelligence providers used by the External Threat agent.

## Structure

```
test_services/
├── test_threat_intel_country_risk.py   # CountryRiskProvider (FATF lists)
├── test_threat_intel_osint.py          # OSINTSearchProvider (DuckDuckGo)
└── test_threat_intel_manager.py        # ThreatIntelManager (orchestration)
```

## Running Tests

### Run all threat intel tests
```bash
cd backend
uv run pytest tests/test_services/ -v
```

### Run specific test file
```bash
uv run pytest tests/test_services/test_threat_intel_country_risk.py -v
uv run pytest tests/test_services/test_threat_intel_osint.py -v
uv run pytest tests/test_services/test_threat_intel_manager.py -v
```

### Run as standalone scripts (for manual testing)
```bash
uv run python tests/test_services/test_threat_intel_country_risk.py
uv run python tests/test_services/test_threat_intel_osint.py
uv run python tests/test_services/test_threat_intel_manager.py
```

## Test Descriptions

### test_threat_intel_country_risk.py
Tests the CountryRiskProvider against FATF lists:
- ✅ Blacklist countries (Iran, North Korea) → 0.95-1.0 confidence
- ✅ Graylist countries (Venezuela, Pakistan) → 0.65-0.85 confidence
- ✅ Elevated risk countries (Russia, China) → 0.35-0.75 confidence
- ✅ Safe countries (Peru) → 0 sources

**Requirements**: None (uses local JSON file)

### test_threat_intel_osint.py
Tests the OSINTSearchProvider with web search:
- ✅ Executes 2-3 DuckDuckGo queries
- ✅ Calculates relevance-based confidence scores
- ✅ Handles timeouts gracefully (10s global timeout)

**Requirements**: Internet connection (can be disabled via config)

### test_threat_intel_manager.py
Tests the full ThreatIntelManager orchestration:
- ✅ All providers run in parallel
- ✅ Results aggregated correctly
- ✅ Multi-source bonus applied
- ✅ High-risk transactions detected (threat level ≥ 0.9)

**Requirements**: Internet connection (for OSINT), optional OpenSanctions API key

## Configuration

These tests respect the settings in `.env`:

```bash
# Enable/disable providers
THREAT_INTEL_ENABLE_OSINT=true
THREAT_INTEL_ENABLE_SANCTIONS=true

# OSINT settings
THREAT_INTEL_OSINT_MAX_RESULTS=5

# Optional API key (test works without it)
OPENSANCTIONS_API_KEY=
```

## Expected Test Times

- **Country Risk**: < 1 second (local JSON lookup)
- **OSINT**: 10-15 seconds (web search + timeout)
- **Manager**: 10-15 seconds (parallel execution, limited by OSINT)

## Notes

- Tests can run offline if `THREAT_INTEL_ENABLE_OSINT=false`
- SanctionsProvider gracefully skips if no API key configured
- All providers handle errors internally (never crash the pipeline)
