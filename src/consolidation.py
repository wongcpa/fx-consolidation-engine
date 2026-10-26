"""
consolidation.py
================
Multi-Entity Financial Statement Consolidation Tool
Consolidates P&L and Balance Sheet across 3 entities with FX translation
and intercompany elimination.

Usage:
  python consolidation.py

You will be prompted for:
  - Entity A trial balance CSV (USD)
  - Entity B trial balance CSV (CAD)
  - Entity C trial balance CSV (GBP)
  - Intercompany eliminations CSV

Expected CSV columns (trial balance):
  account_code, account_name, account_type, debit, credit, currency

Expected CSV columns (eliminations):
  description, account_code, account_name, account_type, entity,
  elim_debit_usd, elim_credit_usd

Account types: REVENUE, COGS, OPEX, ASSET, LIABILITY, EQUITY,
               OTHER_INCOME, OTHER_EXPENSE

Test fixtures:
  entity_a_usd.csv, entity_b_cad.csv, entity_c_gbp.csv,
  intercompany_eliminations.csv

Author: Jimmy Wong, CPA
DATA PRIVACY: All data is processed locally. No data is sent to any
              third party.
"""

import csv
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# SECTION 1: FX TRANSLATION RATES
# ---------------------------------------------------------------------------
FX_RATES = {
    ("CAD", "USD"): (0.7400, 0.7350),
    ("GBP", "USD"): (1.2700, 1.2650),
    ("USD", "USD"): (1.0000, 1.0000),
}

def translate(amount: float, from_ccy: str, to_ccy: str,
              rate_type: str = "average") -> float:
    """Translate an amount from one currency to USD."""
    if from_ccy == to_ccy:
        return amount
    key = (from_ccy, to_ccy)
    if key not in FX_RATES:
        raise ValueError(f"No FX rate defined for {from_ccy} -> {to_ccy}")
    avg_rate, close_rate = FX_RATES[key]
    rate = avg_rate if rate_type == "average" else close_rate
    return round(amount * rate, 2)


# ---------------------------------------------------------------------------
# SECTION 2: FILE INPUT WITH RETRY LOGIC
# ---------------------------------------------------------------------------

EXPECTED_TB_COLUMNS = {
    "account_code", "account_name", "account_type",
    "debit", "credit", "currency"
}
EXPECTED_ELIM_COLUMNS = {
    "description", "account_code", "account_name", "account_type",
    "entity", "elim_debit_usd", "elim_credit_usd"
}

def prompt_for_file(prompt_msg: str, expected_cols: set,
                    max_attempts: int = 3) -> str:
    """
    Prompt the user for a CSV file path, validate it exists and has
    the expected columns. Re-prompts up to max_attempts times on failure.

    Args:
        prompt_msg:   Display message shown to the user.
        expected_cols: Set of column names the CSV must contain.
        max_attempts: Number of retries before exiting.

    Returns:
        Valid file path string.
    """
    for attempt in range(1, max_attempts + 1):
        raw = input(f"\n{prompt_msg}: ").strip()
        path = Path(raw)

        if not path.exists():
            print(f"  ERROR: File not found: '{raw}'")
            if attempt < max_attempts:
                print(f"  Attempt {attempt}/{max_attempts}. Please try again.")
            continue

        if path.suffix.lower() != ".csv":
            print(f"  ERROR: Expected a .csv file, got: '{path.suffix}'")
            if attempt < max_attempts:
                print(f"  Attempt {attempt}/{max_attempts}. Please try again.")
            continue

        # Validate column headers
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])
                missing = expected_cols - headers
                if missing:
                    print(f"  ERROR: CSV missing required columns: "
                          f"{', '.join(sorted(missing))}")
                    print(f"  Expected columns: "
                          f"{', '.join(sorted(expected_cols))}")
                    if attempt < max_attempts:
                        print(f"  Attempt {attempt}/{max_attempts}. "
                              f"Please try again.")
                    continue
        except Exception as e:
            print(f"  ERROR: Could not read file: {e}")
            if attempt < max_attempts:
                print(f"  Attempt {attempt}/{max_attempts}. Please try again.")
            continue

        return str(path)

    print(f"\n  FATAL: Maximum attempts ({max_attempts}) reached. Exiting.")
    sys.exit(1)


def prompt_for_output(default: str = "consolidated_trial_balance.csv") -> str:
    """Prompt for output file path with a sensible default."""
    raw = input(f"\nOutput CSV filename [{default}]: ").strip()
    return raw if raw else default


# ---------------------------------------------------------------------------
# SECTION 3: CSV LOADERS
# ---------------------------------------------------------------------------

def load_trial_balance(filepath: str) -> List[Dict]:
    """Load a trial balance CSV into a list of row dicts."""
    rows = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({
                "code":   row["account_code"].strip(),
                "name":   row["account_name"].strip(),
                "type":   row["account_type"].strip(),
                "debit":  float(row["debit"] or 0),
                "credit": float(row["credit"] or 0),
                "ccy":    row["currency"].strip(),
            })
    return rows


def load_eliminations(filepath: str) -> List[Dict]:
    """Load an intercompany eliminations CSV."""
    elims = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            elims.append({
                "description":  row["description"].strip(),
                "account_code": row["account_code"].strip(),
                "account_name": row["account_name"].strip(),
                "account_type": row["account_type"].strip(),
                "entity":       row["entity"].strip(),
                "elim_debit":   float(row["elim_debit_usd"] or 0),
                "elim_credit":  float(row["elim_credit_usd"] or 0),
                "ccy":          "USD",
            })
    return elims


# ---------------------------------------------------------------------------
# SECTION 4: TRANSLATION & CONSOLIDATION ENGINE
# ---------------------------------------------------------------------------

def translate_trial_balance(tb: List[Dict],
                            entity_name: str) -> List[Dict]:
    """Translate all amounts to USD using appropriate rate type."""
    pl_types = {"REVENUE", "COGS", "OPEX", "OTHER_INCOME", "OTHER_EXPENSE"}
    translated = []
    for row in tb:
        rate_type = "average" if row["type"] in pl_types else "closing"
        translated.append({
            **row,
            "entity":      entity_name,
            "usd_debit":   translate(row["debit"],  row["ccy"], "USD", rate_type),
            "usd_credit":  translate(row["credit"], row["ccy"], "USD", rate_type),
            "rate_type":   rate_type,
        })
    return translated


def consolidate(entities: List[Tuple[str, List[Dict]]],
                eliminations: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate translated trial balances and apply IC eliminations.

    Args:
        entities:     List of (entity_name, trial_balance) tuples.
        eliminations: Loaded eliminations list.

    Returns:
        Dict keyed by account_code with consolidated totals.
    """
    ledger: Dict[str, Dict] = {}

    for entity_name, tb in entities:
        for row in translate_trial_balance(tb, entity_name):
            code = row["code"]
            if code not in ledger:
                ledger[code] = {
                    "code":         code,
                    "name":         row["name"],
                    "type":         row["type"],
                    "total_debit":  0.0,
                    "total_credit": 0.0,
                }
            ledger[code]["total_debit"]  += row["usd_debit"]
            ledger[code]["total_credit"] += row["usd_credit"]

    for elim in eliminations:
        code = elim["account_code"]
        if code not in ledger:
            ledger[code] = {
                "code":         code,
                "name":         elim["account_name"],
                "type":         elim["account_type"],
                "total_debit":  0.0,
                "total_credit": 0.0,
            }
        ledger[code]["total_debit"]  -= elim["elim_debit"]
        ledger[code]["total_credit"] -= elim["elim_credit"]

    return ledger


# ---------------------------------------------------------------------------
# SECTION 5: REPORTING
# ---------------------------------------------------------------------------

def net(row: Dict) -> float:
    """Return net amount with correct sign convention."""
    if row["type"] in {"REVENUE", "LIABILITY", "EQUITY", "OTHER_INCOME"}:
        return row["total_credit"] - row["total_debit"]
    return row["total_debit"] - row["total_credit"]


def print_report(ledger: Dict[str, Dict], report_date: date) -> None:
    """Print consolidated P&L and Balance Sheet to stdout."""
    pl_types = {"REVENUE", "COGS", "OPEX", "OTHER_INCOME", "OTHER_EXPENSE"}
    bs_types = {"ASSET", "LIABILITY", "EQUITY"}

    pl_rows = {c: v for c, v in ledger.items() if v["type"] in pl_types}
    bs_rows = {c: v for c, v in ledger.items() if v["type"] in bs_types}

    div = "=" * 72
    print(f"\n{div}")
    print("  CONSOLIDATED FINANCIAL STATEMENTS — USD")
    print(f"  Period Ending: {report_date.strftime('%B %d, %Y')}")
    print(f"  Entities: Entity A (USD), Entity B (CAD), Entity C (GBP)")
    print(div)

    total_revenue = total_cogs = total_opex = 0.0

    print("\n  CONSOLIDATED INCOME STATEMENT")
    print("  " + "-" * 60)
    for type_label, acct_type in [
        ("Revenue",            "REVENUE"),
        ("Cost of Goods Sold", "COGS"),
        ("Operating Expenses", "OPEX"),
        ("Other Income",       "OTHER_INCOME"),
        ("Other Expense",      "OTHER_EXPENSE"),
    ]:
        rows = {c: v for c, v in pl_rows.items() if v["type"] == acct_type}
        if not rows:
            continue
        print(f"\n  {type_label}")
        for row in sorted(rows.values(), key=lambda x: x["code"]):
            n = net(row)
            print(f"    {row['code']}  {row['name']:<35}  ${n:>14,.2f}")
            if acct_type == "REVENUE":      total_revenue += n
            elif acct_type == "COGS":       total_cogs += n
            elif acct_type == "OPEX":       total_opex += n

    gross_profit    = total_revenue - total_cogs
    operating_income = gross_profit - total_opex
    print(f"\n  {'Gross Profit':<42}  ${gross_profit:>14,.2f}")
    print(f"  {'Operating Income (EBIT)':<42}  ${operating_income:>14,.2f}")

    print(f"\n\n  CONSOLIDATED BALANCE SHEET")
    print("  " + "-" * 60)
    for type_label, acct_type in [
        ("Assets",      "ASSET"),
        ("Liabilities", "LIABILITY"),
        ("Equity",      "EQUITY"),
    ]:
        rows = {c: v for c, v in bs_rows.items() if v["type"] == acct_type}
        if not rows:
            continue
        print(f"\n  {type_label}")
        section_total = 0.0
        for row in sorted(rows.values(), key=lambda x: x["code"]):
            n = net(row)
            print(f"    {row['code']}  {row['name']:<35}  ${n:>14,.2f}")
            section_total += n
        print(f"    {'Total ' + type_label:<39}  ${section_total:>14,.2f}")

    print(f"\n{div}")
    print("  FX Rates — CAD/USD avg: "
          f"{FX_RATES[('CAD','USD')][0]}  close: {FX_RATES[('CAD','USD')][1]}")
    print(f"            GBP/USD avg: "
          f"{FX_RATES[('GBP','USD')][0]}  close: {FX_RATES[('GBP','USD')][1]}")
    print("  IC balances eliminated per eliminations file.")
    print(div)


def export_csv(ledger: Dict[str, Dict], filepath: str) -> None:
    """Export the consolidated ledger to CSV."""
    fieldnames = ["code", "name", "type",
                  "total_debit_usd", "total_credit_usd", "net_usd"]
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(ledger.values(), key=lambda x: x["code"]):
            writer.writerow({
                "code":             row["code"],
                "name":             row["name"],
                "type":             row["type"],
                "total_debit_usd":  round(row["total_debit"],  2),
                "total_credit_usd": round(row["total_credit"], 2),
                "net_usd":          round(
                    row["total_credit"] - row["total_debit"], 2),
            })
    print(f"\n  ✔ CSV export saved to: {filepath}")


# ---------------------------------------------------------------------------
# SECTION 6: MAIN
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  MULTI-ENTITY CONSOLIDATION TOOL")
    print("  Consolidates USD / CAD / GBP entities to USD")
    print("=" * 60)
    print("\nYou will be prompted for 4 CSV files.")
    print("Test fixtures: entity_a_usd.csv, entity_b_cad.csv,")
    print("               entity_c_gbp.csv, intercompany_eliminations.csv")

    path_a = prompt_for_file(
        "Entity A trial balance CSV (USD parent)",
        EXPECTED_TB_COLUMNS)
    path_b = prompt_for_file(
        "Entity B trial balance CSV (CAD subsidiary)",
        EXPECTED_TB_COLUMNS)
    path_c = prompt_for_file(
        "Entity C trial balance CSV (GBP subsidiary)",
        EXPECTED_TB_COLUMNS)
    path_e = prompt_for_file(
        "Intercompany eliminations CSV",
        EXPECTED_ELIM_COLUMNS)

    output_path = prompt_for_output()

    print("\nLoading data...")
    entities = [
        ("Entity A (USD)", load_trial_balance(path_a)),
        ("Entity B (CAD)", load_trial_balance(path_b)),
        ("Entity C (GBP)", load_trial_balance(path_c)),
    ]
    eliminations = load_eliminations(path_e)

    print("Translating currencies and applying eliminations...")
    ledger = consolidate(entities, eliminations)

    print_report(ledger, report_date=date.today())
    export_csv(ledger, output_path)


if __name__ == "__main__":
    main()
