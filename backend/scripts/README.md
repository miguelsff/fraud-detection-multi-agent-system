# Backend Scripts

Utility scripts for the Fraud Detection Multi-Agent System.

---

## 📊 demo.py

**End-to-end demonstration of the complete fraud detection pipeline.**

### Usage

```bash
cd backend
uv run python scripts/demo.py
```

### What It Does

The demo script provides a comprehensive walkthrough of the entire system:

1. **Policy Ingestion**
   - Loads fraud policies from `backend/policies/` directory
   - Ingests documents into ChromaDB vector store
   - Reports number of policy chunks indexed

2. **Test Data Loading**
   - Reads 6 synthetic transactions from `backend/data/synthetic_data.json`
   - Covers all decision types: APPROVE, CHALLENGE, BLOCK, ESCALATE_TO_HUMAN

3. **Sequential Analysis**
   - Analyzes each transaction through the 8-agent pipeline
   - Real-time progress display with live results
   - Tracks processing time and confidence for each decision

4. **Results Summary**
   - Formatted table showing all transactions
   - Expected vs actual decisions comparison
   - Accuracy metrics and performance statistics
   - Average confidence and processing time

5. **Debate Example**
   - Displays a complete adversarial debate from one transaction
   - Shows Pro-Fraud agent's argument, confidence, and evidence
   - Shows Pro-Customer agent's counter-argument and evidence
   - Final arbiter decision with customer explanation

### Prerequisites

- PostgreSQL running (via `docker compose up -d` from project root)
- Ollama running with llama3.2 model (`ollama pull llama3.2`)
- Backend dependencies installed (`uv sync`)
- Policies directory exists at `backend/policies/`

### Example Output

```
═══ Fraud Detection Multi-Agent System ═══
         End-to-End Pipeline Demo

Step 1: Ingesting fraud policies into ChromaDB
✓ Successfully ingested 24 policy chunks

Step 2: Loading synthetic test data
✓ Loaded 6 test transactions

Step 3: Analyzing transactions (sequential)
  ✓ T-1001: CHALLENGE (72%) — 4.2s
  ✓ T-1002: BLOCK (94%) — 5.1s
  ✓ T-1003: APPROVE (89%) — 3.8s
  ✓ T-1004: ESCALATE_TO_HUMAN (65%) — 4.5s
  ✓ T-1005: CHALLENGE (78%) — 4.0s
  ✓ T-1006: BLOCK (96%) — 5.3s

Step 4: Results Summary
╭─────────── Fraud Detection Analysis Results ──────────╮
│ ID       Expected           Actual             ✓  ... │
│ T-1001   CHALLENGE          CHALLENGE          ✓  ... │
│ T-1002   BLOCK              BLOCK              ✓  ... │
│ T-1003   APPROVE            APPROVE            ✓  ... │
│ T-1004   ESCALATE_TO_HUMAN  ESCALATE_TO_HUMAN  ✓  ... │
│ T-1005   CHALLENGE          CHALLENGE          ✓  ... │
│ T-1006   BLOCK              BLOCK              ✓  ... │
╰────────────────────────────────────────────────────────╯

Summary Statistics:
  Total Transactions: 6
  Correct Predictions: 6/6
  Accuracy: 100.0%
  Average Confidence: 82.3%
  Average Processing Time: 4.48s

Step 5: Adversarial Debate Example

Transaction: T-1001
  Amount: 1800.00 PEN
  Country: PE | Channel: web
  Timestamp: 2025-01-15T03:15:00Z

╭──────────── ⚠ Pro-Fraud Agent ────────────╮
│ Argument:                                  │
│ La transacción de S/1800 a las 03:15      │
│ representa 3.6x el promedio del cliente.  │
│ El horario nocturno combinado con el      │
│ monto elevado coincide con FP-01...       │
│                                            │
│ Confidence: 78.0%                          │
│                                            │
│ Evidence:                                  │
│   • amount_ratio: 3.6x                     │
│   • off_hours: 03:15                       │
│   • policy_match: FP-01                    │
╰────────────────────────────────────────────╯

╭──────────── ✓ Pro-Customer Agent ─────────╮
│ Argument:                                  │
│ El cliente ha realizado compras           │
│ anteriores por montos similares.          │
│ El dispositivo D-01 es conocido y         │
│ el país coincide con su perfil...         │
│                                            │
│ Confidence: 55.0%                          │
│                                            │
│ Evidence:                                  │
│   • known_device: D-01                     │
│   • same_country: PE                       │
│   • merchant_history: positive             │
╰────────────────────────────────────────────╯

╭──────────── ⚖ Arbiter Decision ───────────╮
│ Decision: CHALLENGE                        │
│ Confidence: 72.0%                          │
│                                            │
│ Customer Explanation:                      │
│ Hemos detectado actividad inusual en      │
│ su cuenta. Por seguridad, necesitamos     │
│ verificar esta transacción.               │
╰────────────────────────────────────────────╯

✓ Demo completed successfully!
```

### Features

- **Rich Terminal UI**: Colored output, tables, and panels using the `rich` library
- **Real-time Progress**: Live updates as each transaction is processed
- **Performance Metrics**: Detailed timing and confidence statistics
- **Debate Visualization**: Complete view of the adversarial argumentation process
- **Error Handling**: Graceful degradation on policy ingestion or analysis failures

---

## 🔍 verify_api.py

**API verification and testing script.**

Verifies that the FastAPI backend is running and responds correctly to health checks and basic endpoints.

### Usage

```bash
cd backend
uv run python scripts/verify_api.py
```

---

## Contributing

When adding new scripts:
1. Add them to this directory (`backend/scripts/`)
2. Include a shebang line (`#!/usr/bin/env python`)
3. Add comprehensive docstrings
4. Document usage in this README
5. Make executable on Unix systems (`chmod +x`)
