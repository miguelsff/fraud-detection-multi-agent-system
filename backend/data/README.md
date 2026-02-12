# Synthetic Test Data

This directory contains synthetic transaction data for testing the fraud detection pipeline.

## Files

- `synthetic_data.json` — 6 test transactions covering all possible outcomes (APPROVE, CHALLENGE, BLOCK, ESCALATE_TO_HUMAN)

## Test Scenarios

### T-1001 (CHALLENGE)
- **Amount**: S/1,800 (3.6x average)
- **Country**: PE (usual)
- **Time**: 03:15 (off-hours)
- **Device**: D-01 (known)
- **Reason**: High amount + off-hours, but known device and usual country

### T-1002 (BLOCK)
- **Amount**: $8,500 (17x average)
- **Country**: NG (Nigeria, unusual)
- **Time**: 02:00 (off-hours)
- **Device**: D-99 (unknown)
- **Reason**: Very high amount + unusual country + unknown device + off-hours

### T-1003 (APPROVE)
- **Amount**: S/250 (0.5x average)
- **Country**: PE (usual)
- **Time**: 14:30 (normal)
- **Device**: D-03 (known)
- **Reason**: Low amount + usual country + normal hours + known device — normal profile

### T-1004 (ESCALATE_TO_HUMAN)
- **Amount**: $2,000 (4x average)
- **Country**: CO (Colombia, new but nearby)
- **Device**: D-01 (known)
- **Reason**: Ambiguous — high amount but known device, new country but low-risk neighbor

### T-1005 (CHALLENGE)
- **Amount**: S/3,000 (6x average)
- **Country**: PE (usual)
- **Time**: 10:00 (normal)
- **Device**: D-05 (new)
- **Reason**: High amount + new device, but usual country and normal hours

### T-1006 (BLOCK)
- **Amount**: $15,000 (30x average)
- **Country**: RU (Russia, high-risk)
- **Time**: 01:00 (off-hours)
- **Device**: D-88 (new)
- **Reason**: Extremely high amount + high-risk country + unknown device + off-hours — all risk factors

## Running Tests

```bash
# From backend/ directory

# Install rich dependency (if not already installed)
python -m uv sync

# Run seed & test (sequential)
python -m uv run python seed_test.py

# Run seed & test (parallel)
python -m uv run python seed_test.py --parallel

# Or use the service directly
python -m uv run python -m app.services.seed_service
python -m uv run python -m app.services.seed_service --parallel
```

## Expected Output

The script will:
1. Load all 6 transactions from `synthetic_data.json`
2. Run fraud analysis pipeline on each transaction
3. Display a table comparing expected vs. actual outcomes
4. Show accuracy statistics

Example output:

```
═══ Fraud Detection Seed & Test ═══

✓ Loaded 6 transactions from synthetic_data.json

Running 6 transaction analyses
Mode: Sequential

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Transaction  ┃ Expected         ┃ Actual           ┃ Match ┃ Confidence ┃ Reason                                           ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ T-1001       │ CHALLENGE        │ CHALLENGE        │   ✓   │       0.82 │ Monto alto (3.6x promedio) + fuera de horario…   │
│ T-1002       │ BLOCK            │ BLOCK            │   ✓   │       0.95 │ Monto muy alto (17x promedio) + país inusual…    │
│ T-1003       │ APPROVE          │ APPROVE          │   ✓   │       0.98 │ Monto bajo (0.5x promedio) + país usual + hora…  │
│ T-1004       │ ESCALATE_TO_HUMAN│ ESCALATE_TO_HUMAN│   ✓   │       0.65 │ Ambiguo: monto alto (4x promedio) pero device…   │
│ T-1005       │ CHALLENGE        │ CHALLENGE        │   ✓   │       0.79 │ Monto alto (6x promedio) + device nuevo, pero…   │
│ T-1006       │ BLOCK            │ BLOCK            │   ✓   │       0.97 │ Monto extremadamente alto (30x promedio) + pa…   │
└──────────────┴──────────────────┴──────────────────┴───────┴────────────┴──────────────────────────────────────────────────────┘

Summary:
  Total: 6
  Matches: 6
  Mismatches: 0
  Accuracy: 100.0%

✓ Testing completed successfully!
```

## Data Format

Each entry in `synthetic_data.json` contains:

```json
{
  "transaction": {
    "transaction_id": "T-1001",
    "customer_id": "C-501",
    "amount": 1800.00,
    "currency": "PEN",
    "country": "PE",
    "channel": "web",
    "device_id": "D-01",
    "timestamp": "2025-01-15T03:15:00Z",
    "merchant_id": "M-200"
  },
  "customer_behavior": {
    "customer_id": "C-501",
    "usual_amount_avg": 500.00,
    "usual_hours": "08:00-22:00",
    "usual_countries": ["PE"],
    "usual_devices": ["D-01", "D-02"]
  },
  "expected_outcome": "CHALLENGE",
  "reason": "Explanation of why this outcome is expected"
}
```
