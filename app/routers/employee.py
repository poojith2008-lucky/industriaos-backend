from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os, shutil
from datetime import date

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.employee import Employee
from app.models.leave import Leave, LeaveStatusEnum
from app.models.payroll import Payroll
from app.schemas.schemas import LeaveCreate, LeaveOut, PayrollOut, EmployeeUpdate

router = APIRouter(prefix="/api/employee", tags=["Employee"])


def _get_my_employee(current_user: User, db: Session) -> Employee:
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise HTTPException(404, "Employee profile not found")
    return emp


# ── PROFILE ───────────────────────────────────────────────
@router.get("/profile")
def my_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = _get_my_employee(current_user, db)
    return {
        "id": emp.id,
        "name": current_user.name,
        "email": current_user.email,
        "department": emp.department,
        "position": emp.position,
        "base_salary": emp.base_salary,
        "phone": emp.phone,
        "address": emp.address,
        "emergency_contact": emp.emergency_contact,
        "profile_picture": emp.profile_picture,
        "join_date": emp.join_date,
    }


@router.put("/profile")
def update_my_profile(payload: EmployeeUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = _get_my_employee(current_user, db)
    allowed = {"phone", "address", "emergency_contact"}
    for k, v in payload.model_dump(exclude_none=True).items():
        if k in allowed:
            setattr(emp, k, v)
    db.commit(); db.refresh(emp)
    return {"message": "Profile updated"}


@router.post("/profile/picture")
async def upload_picture(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = _get_my_employee(current_user, db)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext      = file.filename.split(".")[-1]
    filename = f"profile_{emp.id}.{ext}"
    path     = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    emp.profile_picture = path
    db.commit()
    return {"message": "Profile picture updated", "path": path}


# ── LEAVE ─────────────────────────────────────────────────
@router.post("/leaves", response_model=LeaveOut)
def apply_leave(payload: LeaveCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp   = _get_my_employee(current_user, db)
    delta = (payload.end_date - payload.start_date).days + 1
    if delta <= 0:
        raise HTTPException(400, "End date must be after start date")
    leave = Leave(
        employee_id=emp.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=delta,
        reason=payload.reason,
        status=LeaveStatusEnum.PENDING
    )
    db.add(leave); db.commit(); db.refresh(leave)
    return leave


@router.get("/leaves", response_model=List[LeaveOut])
def my_leaves(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = _get_my_employee(current_user, db)
    return db.query(Leave).filter(Leave.employee_id == emp.id).order_by(Leave.created_at.desc()).all()


@router.get("/leave-balance")
def leave_balance(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp  = _get_my_employee(current_user, db)
    from sqlalchemy import func
    used = db.query(func.sum(Leave.days)).filter(
        Leave.employee_id == emp.id,
        Leave.status == LeaveStatusEnum.APPROVED
    ).scalar() or 0
    total = 24
    return {"total": total, "used": used, "remaining": total - used}


# ── PAYROLL ───────────────────────────────────────────────
@router.get("/payroll", response_model=List[PayrollOut])
def my_payroll(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = _get_my_employee(current_user, db)
    return db.query(Payroll).filter(Payroll.employee_id == emp.id).order_by(
        Payroll.year.desc(), Payroll.month.desc()
    ).all()


@router.get("/payroll/latest")
def latest_payroll(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = _get_my_employee(current_user, db)
    p   = db.query(Payroll).filter(Payroll.employee_id == emp.id).order_by(
        Payroll.year.desc(), Payroll.month.desc()
    ).first()
    if not p: return {"message": "No payroll found"}
    return p


# ── DASHBOARD ─────────────────────────────────────────────
@router.get("/dashboard")
def employee_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    emp = _get_my_employee(current_user, db)
    from sqlalchemy import func
    used_leaves = db.query(func.sum(Leave.days)).filter(
        Leave.employee_id == emp.id,
        Leave.status == LeaveStatusEnum.APPROVED
    ).scalar() or 0
    pending_leaves = db.query(Leave).filter(
        Leave.employee_id == emp.id,
        Leave.status == LeaveStatusEnum.PENDING
    ).count()
    latest = db.query(Payroll).filter(Payroll.employee_id == emp.id).order_by(
        Payroll.year.desc(), Payroll.month.desc()
    ).first()
    return {
        "leave_balance": max(0, 24 - used_leaves),
        "used_leave": used_leaves,
        "pending_leave": pending_leaves,
        "last_salary": latest.net_salary if latest else 0,
        "last_salary_status": latest.status if latest else "N/A",
        "last_salary_month": f"{latest.month}/{latest.year}" if latest else "N/A",
    }