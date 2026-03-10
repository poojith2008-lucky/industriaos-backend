from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.revenue import Revenue
from app.models.payroll import Payroll, PayrollStatusEnum
from app.models.leave import Leave, LeaveStatusEnum
from app.models.employee import Employee
from datetime import datetime
from typing import List, Dict

def run_ai_checks(db: Session) -> List[Dict]:
    warnings = []
    now           = datetime.utcnow()
    current_month = now.month
    current_year  = now.year

    # ── 1. Salary > 50% of revenue ──────────────────────────
    revenue = db.query(Revenue).filter(
        Revenue.month == current_month, Revenue.year == current_year
    ).first()
    total_payroll = db.query(func.sum(Payroll.net_salary)).filter(
        Payroll.month == current_month, Payroll.year == current_year
    ).scalar() or 0

    if revenue and revenue.amount > 0:
        ratio = (total_payroll / revenue.amount) * 100
        if ratio >= 50:
            warnings.append({
                "level": "CRITICAL", "icon": "🔴",
                "message": f"Salary-to-Revenue ratio is {ratio:.1f}% — exceeds 50% threshold!",
                "metric": round(ratio, 1)
            })
        elif ratio >= 40:
            warnings.append({
                "level": "WARNING", "icon": "🟠",
                "message": f"Salary-to-Revenue ratio at {ratio:.1f}% — approaching 50% limit",
                "metric": round(ratio, 1)
            })

    # ── 2. Revenue drop 3 consecutive months ────────────────
    recent = db.query(Revenue).order_by(
        Revenue.year.desc(), Revenue.month.desc()
    ).limit(4).all()

    if len(recent) >= 3:
        drops = all(
            recent[i].amount < recent[i+1].amount
            for i in range(min(3, len(recent)-1))
        )
        if drops:
            warnings.append({
                "level": "ALERT", "icon": "🟠",
                "message": "Revenue has dropped for 3 consecutive months!",
                "metric": None
            })

    # ── 3. Profit negative ──────────────────────────────────
    if revenue and revenue.profit < 0:
        warnings.append({
            "level": "CRITICAL", "icon": "🔴",
            "message": f"Net profit is NEGATIVE this month: {revenue.profit:,.0f}",
            "metric": revenue.profit
        })

    # ── 4. Pending payroll > 30% ────────────────────────────
    total_emp      = db.query(Employee).count()
    pending_payroll = db.query(Payroll).filter(
        Payroll.month == current_month,
        Payroll.year  == current_year,
        Payroll.status == PayrollStatusEnum.PENDING
    ).count()

    if total_emp > 0:
        pending_pct = (pending_payroll / total_emp) * 100
        if pending_pct > 30:
            warnings.append({
                "level": "WARNING", "icon": "🟡",
                "message": f"{pending_pct:.0f}% of payrolls are still pending!",
                "metric": round(pending_pct, 1)
            })

    # ── 5. Leave spike ──────────────────────────────────────
    this_month_leaves = db.query(Leave).filter(
        func.extract("month", Leave.created_at) == current_month,
        func.extract("year",  Leave.created_at) == current_year
    ).count()

    last_month = current_month - 1 if current_month > 1 else 12
    last_year  = current_year if current_month > 1 else current_year - 1
    last_month_leaves = db.query(Leave).filter(
        func.extract("month", Leave.created_at) == last_month,
        func.extract("year",  Leave.created_at) == last_year
    ).count()

    if last_month_leaves > 0 and this_month_leaves > last_month_leaves * 1.3:
        warnings.append({
            "level": "NOTICE", "icon": "🟡",
            "message": f"Leave requests spiked {((this_month_leaves/last_month_leaves)-1)*100:.0f}% above last month",
            "metric": this_month_leaves
        })

    if not warnings:
        warnings.append({
            "level": "OK", "icon": "🟢",
            "message": "All systems healthy — no anomalies detected",
            "metric": None
        })

    return warnings


def get_revenue_prediction(db: Session) -> Dict:
    revenues = db.query(Revenue).order_by(
        Revenue.year.asc(), Revenue.month.asc()
    ).limit(6).all()

    if len(revenues) < 2:
        return {"predicted": 0, "confidence": 0, "trend": "insufficient_data"}

    amounts    = [r.amount for r in revenues]
    avg_growth = sum(
        (amounts[i] - amounts[i-1]) / amounts[i-1]
        for i in range(1, len(amounts))
        if amounts[i-1] > 0
    ) / max(len(amounts) - 1, 1)

    last      = amounts[-1]
    predicted = last * (1 + avg_growth)
    confidence = min(95, 60 + len(revenues) * 5)

    return {
        "predicted": round(predicted, 2),
        "growth_pct": round(avg_growth * 100, 1),
        "confidence": confidence,
        "trend": "upward" if avg_growth > 0 else "downward"
    }