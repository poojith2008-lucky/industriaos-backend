from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.core.dependencies import require_admin
from app.core.security import hash_password
from app.models.user import User, RoleEnum
from app.models.employee import Employee
from app.models.payroll import Payroll
from app.models.revenue import Revenue, ActivityLog, EmailLog
from app.schemas.schemas import UserCreate, UserOut, RevenueCreate, RevenueOut
from app.services.ai_engine import run_ai_checks, get_revenue_prediction
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── DASHBOARD STATS ──────────────────────────────────────
@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _=Depends(require_admin)):
    now = datetime.utcnow()
    total_employees = db.query(Employee).count()
    total_hr        = db.query(User).filter(User.role == RoleEnum.HR, User.is_active == True).count()
    total_payroll   = db.query(func.sum(Payroll.net_salary)).filter(
        Payroll.month == now.month, Payroll.year == now.year
    ).scalar() or 0
    revenue = db.query(Revenue).filter(
        Revenue.month == now.month, Revenue.year == now.year
    ).first()

    return {
        "total_employees": total_employees,
        "total_hr": total_hr,
        "monthly_payroll": round(total_payroll, 2),
        "revenue": revenue.amount if revenue else 0,
        "expense": revenue.expense if revenue else 0,
        "profit": revenue.profit if revenue else 0,
        "salary_to_revenue_ratio": round((total_payroll / revenue.amount * 100), 1) if revenue and revenue.amount > 0 else 0,
    }


# ── AI WARNINGS ──────────────────────────────────────────
@router.get("/ai-warnings")
def ai_warnings(db: Session = Depends(get_db), _=Depends(require_admin)):
    return run_ai_checks(db)


# ── REVENUE PREDICTION ───────────────────────────────────
@router.get("/revenue-prediction")
def revenue_prediction(db: Session = Depends(get_db), _=Depends(require_admin)):
    return get_revenue_prediction(db)


# ── CREATE HR ACCOUNT ────────────────────────────────────
@router.post("/create-hr", response_model=UserOut)
def create_hr(payload: UserCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if payload.role != RoleEnum.HR:
        raise HTTPException(400, "This endpoint creates HR accounts only")
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    user = User(
        name=payload.name, email=payload.email,
        hashed_password=hash_password(payload.password), role=RoleEnum.HR
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _log(db, admin.id, f"Created HR account: {user.email}")
    return user


# ── DEACTIVATE HR ─────────────────────────────────────────
@router.patch("/deactivate-hr/{user_id}")
def deactivate_hr(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id, User.role == RoleEnum.HR).first()
    if not user:
        raise HTTPException(404, "HR user not found")
    user.is_active = False
    db.commit()
    _log(db, admin.id, f"Deactivated HR account: {user.email}")
    return {"message": "HR account deactivated"}


# ── LIST ALL HR ───────────────────────────────────────────
@router.get("/hr-list", response_model=List[UserOut])
def list_hr(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(User).filter(User.role == RoleEnum.HR).all()


# ── REVENUE MANAGEMENT ────────────────────────────────────
@router.post("/revenue", response_model=RevenueOut)
def add_revenue(payload: RevenueCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    existing = db.query(Revenue).filter(
        Revenue.month == payload.month, Revenue.year == payload.year
    ).first()
    if existing:
        existing.amount  = payload.amount
        existing.expense = payload.expense
        existing.profit  = payload.amount - payload.expense
        existing.notes   = payload.notes
        db.commit()
        db.refresh(existing)
        return existing
    rev = Revenue(
        month=payload.month, year=payload.year,
        amount=payload.amount, expense=payload.expense,
        profit=payload.amount - payload.expense,
        notes=payload.notes, uploaded_by=admin.id
    )
    db.add(rev)
    db.commit()
    db.refresh(rev)
    _log(db, admin.id, f"Revenue added for {payload.month}/{payload.year}: {payload.amount}")
    return rev


@router.get("/revenue", response_model=List[RevenueOut])
def get_revenue(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Revenue).order_by(Revenue.year.desc(), Revenue.month.desc()).all()


# ── ACTIVITY LOGS ─────────────────────────────────────────
@router.get("/activity-logs")
def activity_logs(limit: int = 50, db: Session = Depends(get_db), _=Depends(require_admin)):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return [{"id": l.id, "action": l.action, "detail": l.detail, "user": l.user.name, "created_at": l.created_at} for l in logs]


# ── EMAIL LOGS ────────────────────────────────────────────
@router.get("/email-logs")
def email_logs(db: Session = Depends(get_db), _=Depends(require_admin)):
    logs = db.query(EmailLog).order_by(EmailLog.sent_at.desc()).limit(50).all()
    return [{"id": l.id, "subject": l.subject, "recipients_count": len(l.recipients), "department": l.department, "sent_by": l.sender.name, "sent_at": l.sent_at} for l in logs]


# ── HELPER ────────────────────────────────────────────────
def _log(db, user_id, action, detail=None):
    db.add(ActivityLog(user_id=user_id, action=action, detail=detail))
    db.commit()