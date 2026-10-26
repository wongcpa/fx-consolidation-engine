# fx-consolidation-engine

**Multi-entity financial statement consolidation with FX translation and intercompany elimination.**

Built to reflect month-end close consolidation at a multi-entity SaaS organization operating across USD, CAD, and GBP using Xero. Produces a consolidated P&L and Balance Sheet in USD, applying IAS 21 translation rates and eliminating intercompany balances per IFRS 10.

[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE) [![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org) [![Tests: pytest](https://img.shields.io/badge/Tests-pytest-green.svg)](tests/) [![100% Local](https://img.shields.io/badge/Data%20Privacy-100%25%20Local-brightgreen.svg)](#data-privacy)

---

## Live Demo
**[Try it live →](https://www.wong.cpa/fx-consolidation-engine/src/)**. Or open `src/index.html` locally in any browser — no server, no install, no data upload. Drop fixture CSVs from `tests/fixtures/` to see a full consolidation instantly.

---

## Features

| Feature | Detail |
|---|---|
| FX Translation | Current rate method: assets and liabilities at closing, P&L at average, equity at historical (IAS 21 / ASC 830) |
| CTA | Each entity's translation difference booked to Cumulative Translation Adjustment in equity (OCI) |
| IC Elimination | Balanced USD journal entries remove intercompany revenue, charges, receivables and payables (IFRS 10) |
| Built-in checks | Confirms Assets = Liabilities + Equity and reports any intercompany residual |
| Input validation | Rejects unbalanced trial balances, unbalanced eliminations and conflicting account types |
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
│   ├── test_consolidation.py # pytest suite — FX, elimination, integration
│   └── fixtures/
│       ├── entity_a_usd.csv
│       ├── entity_b_cad.csv
│       ├── entity_c_gbp.csv
│       └── intercompany_eliminations.csv
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
# Prompts for each file — enter paths from tests/fixtures/
```

**Tests:**
```bash
pip install pytest && pytest tests/ -v
```

---

## Input CSV Columns (Trial Balance)

`account_code` · `account_name` · `account_type` · `debit` · `credit` · `currency`

Account types: `ASSET` `LIABILITY` `EQUITY` `REVENUE` `COGS` `OPEX` `OTHER_INCOME` `OTHER_EXPENSE`

All entities must use a common group chart of accounts (the same code means the same account in every trial balance). Each trial balance must balance in its local currency.

## Sample Data

The fixtures model a USD parent with CAD and GBP subsidiaries. Entity A charges Entity B USD 54,200; Entity B carries the payable remeasured at the closing rate, so it eliminates exactly against Entity A's receivable. The consolidated result balances at $1,513,829 with a translation loss of $9,041 in CTA, since CAD and GBP weakened against their historical rates.

Simplification: equity is translated at a single historical rate per currency. In practice, opening retained earnings carries forward from the prior period's translated balance.

---

## Standards Applied

- **IAS 21** — FX translation: assets and liabilities at closing rate, P&L at average rate, equity at historical rates, differences to OCI
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
