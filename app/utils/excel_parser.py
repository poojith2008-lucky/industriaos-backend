import pandas as pd
import io
from typing import List, Dict


def parse_payroll_excel(content: bytes) -> List[Dict]:
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Could not read Excel file: {e}")

    # ── Normalize column names ───────────────────────────────
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"employee_id", "base_salary", "bonus", "deductions"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    records = []
    for _, row in df.iterrows():
        try:
            base       = float(row["base_salary"])
            bonus      = float(row.get("bonus", 0) or 0)
            deductions = float(row.get("deductions", 0) or 0)
            net        = base + bonus - deductions
            records.append({
                "employee_id": int(row["employee_id"]),
                "base_salary": base,
                "bonus":       bonus,
                "deductions":  deductions,
                "net_salary":  net,
            })
        except Exception as e:
            print(f"[EXCEL PARSER] Skipping row: {e}")
            continue

    if not records:
        raise ValueError("No valid records found in Excel file")

    return records


def parse_revenue_excel(content: bytes) -> List[Dict]:
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Could not read Excel file: {e}")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"month", "year", "amount", "expense"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    records = []
    for _, row in df.iterrows():
        try:
            amount  = float(row["amount"])
            expense = float(row["expense"])
            records.append({
                "month":   int(row["month"]),
                "year":    int(row["year"]),
                "amount":  amount,
                "expense": expense,
                "profit":  amount - expense,
                "notes":   str(row.get("notes", "") or ""),
            })
        except Exception as e:
            print(f"[REVENUE PARSER] Skipping row: {e}")
            continue

    if not records:
        raise ValueError("No valid records found in Excel file")

    return records