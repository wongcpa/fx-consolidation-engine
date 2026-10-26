# fx-consolidation-engine

**Multi-entity financial statement consolidation with FX translation and intercompany elimination.**

Built to reflect month-end close consolidation at a multi-entity SaaS organization operating across USD, CAD, and GBP using Xero. Produces a consolidated P&L and Balance Sheet in USD, applying IAS 21 translation rates and eliminating intercompany balances per IFRS 10.

[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE) [![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org) [![Tests: pytest](https://img.shields.io/badge/Tests-pytest-green.svg)](tests/) [![100% Local](https://img.shields.io/badge/Data%20Privacy-100%25%20Local-brightgreen.svg)](#data-privacy)

---

## Live Demo
Open `src/index.html` in any browser — no server, no install, no data upload. Drop fixture CSVs from `fixtures/` to see a full consolidation instantly.

---

## Features

| Feature | Detail |
|---|---|
| FX Translation | P&L at period-average; B/S at period-closing (IAS 21 / ASC 830) |
| IC Elimination | Removes intercompany revenue, receivables, payables (IFRS 10) |
| Multi-currency | USD parent · CAD subsidiary · GBP subsidiary → consolidated USD |
| Editable FX rates | Web app allows live rate adjustment before consolidating |
| CSV export | Machine-readable consolidated trial balance |
| CLI tool | Python script with file prompts and 3-retry validation |
| Zero dependencies | Web app: browser-native JS only · CLI: Python stdlib only |

---

## Repository Structure

```
fx-consolidation-engine/
├── src/
│   ├── index.html            # Browser web app (drag & drop, no install)
│   └── consolidation.py      # Python CLI with file input prompts
├── tests/
│   └── test_consolidation.py # pytest suite — FX, elimination, integration
├── fixtures/
│   ├── entity_a_usd.csv
│   ├── entity_b_cad.csv
│   ├── entity_c_gbp.csv
│   └── intercompany_eliminations.csv
├── requirements.txt
├── .gitignore
└── LICENSE
```

---

## Quick Start

**Web app:** `open src/index.html` → drop fixture CSVs → click Consolidate.

**CLI:**
```bash
git clone https://github.com/wongcpa/fx-consolidation-engine.git
cd fx-consolidation-engine
python src/consolidation.py
# Prompts for each file — enter paths from fixtures/
```

**Tests:**
```bash
pip install pytest && pytest tests/ -v
```

---

## Input CSV Columns (Trial Balance)

`account_code` · `account_name` · `account_type` · `debit` · `credit` · `currency`

Account types: `ASSET` `LIABILITY` `EQUITY` `REVENUE` `COGS` `OPEX` `OTHER_INCOME` `OTHER_EXPENSE`

---

## Standards Applied

- **IAS 21** — FX translation: P&L at average rate, B/S at closing rate
- **IFRS 10** — Consolidated financial statements: full IC elimination
- **ASC 830** — US GAAP equivalent FX translation methodology

---

## Data Privacy
All processing is local. No data is uploaded to any server or API.

---

## Author

**Jimmy Wong, CPA (WA), CPA (Canada)** — Finance Systems & AI Automation
[www.wong.cpa](https://www.wong.cpa) · [LinkedIn](https://www.linkedin.com/in/wongjimmy/) · [GitHub @wongcpa](https://github.com/wongcpa)

*For accounting analysis only. Consult a qualified CPA for final consolidated statement preparation.*
