from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date
import os, shutil

from app.database import get_db
from app.core.dependencies import require_hr
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User, RoleEnum
from app.models.employee import Employee
from app.models.leave import Leave, LeaveStatusEnum
from app.models.payroll import Payroll, PayrollStatusEnum
from app.models.revenue import ActivityLog, EmailLog
from app.schemas.schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeOut,
    LeaveOut, LeaveReview, PayrollCreate, PayrollOut
)
from app.services.email_service import send_bulk_announcement, send_salary_slip
from app.utils.qr_generator import generate_payroll_qr
from app.utils.excel_parser import parse_payroll_excel

router = APIRouter(prefix="/api/hr", tags=["HR"])


# ── DASHBOARD STATS ──────────────────────────────────────
@router.get("/stats")
def hr_stats(db: Session = Depends(get_db), _=Depends(require_hr)):
    now = datetime.utcnow()
    return {
        "total_employees": db.query(Employee).count(),
        "pending_leaves": db.query(Leave).filter(Leave.status == LeaveStatusEnum.PENDING).count(),
        "pending_payroll": db.query(Payroll).filter(
            Payroll.month == now.month, Payroll.year == now.year,
            Payroll.status == PayrollStatusEnum.PENDING
        ).count(),
        "monthly_expense": db.query(func.sum(Payroll.net_salary)).filter(
            Payroll.month == now.month, Payroll.year == now.year
        ).scalar() or 0,
    }


# ── EMPLOYEE CRUD ─────────────────────────────────────────
@router.post("/employees", response_model=EmployeeOut)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), hr=Depends(require_hr)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        name=payload.name, email=payload.email,
        hashed_password=hash_password(payload.password), role=RoleEnum.EMPLOYEE
    )
    db.add(user); db.flush()
    emp = Employee(
        user_id=user.id, department=payload.department,
        position=payload.position, base_salary=payload.base_salary,
        phone=payload.phone, address=payload.address,
        emergency_contact=payload.emergency_contact,
        join_date=payload.join_date or date.today()
    )
    db.add(emp); db.commit(); db.refresh(emp)
    _log(db, hr.id, f"Created employee: {payload.name}")
    return emp


@router.get("/employees", response_model=List[EmployeeOut])
def list_employees(
    department: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(require_hr)
):
    q = db.query(Employee).join(User)
    if department:
        q = q.filter(Employee.department == department)
    if search:
        q = q.filter(User.name.ilike(f"%{search}%"))
    return q.all()


@router.get("/employees/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: int, db: Session = Depends(get_db), _=Depends(require_hr)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp: raise HTTPException(404, "Employee not found")
    return emp


@router.put("/employees/{emp_id}", response_model=EmployeeOut)
def update_employee(emp_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), hr=Depends(require_hr)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp: raise HTTPException(404, "Employee not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(emp, k, v)
    db.commit(); db.refresh(emp)
    _log(db, hr.id, f"Updated employee ID {emp_id}")
    return emp


@router.delete("/employees/{emp_id}")
def delete_employee(emp_id: int, db: Session = Depends(get_db), hr=Depends(require_hr)):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp: raise HTTPException(404, "Employee not found")
    emp.user.is_active = False
    db.commit()
    _log(db, hr.id, f"Deactivated employee ID {emp_id}")
    return {"message": "Employee deactivated"}


# ── LEAVE MANAGEMENT ─────────────────────────────────────
@router.get("/leaves", response_model=List[LeaveOut])
def get_leaves(status: Optional[str] = None, db: Session = Depends(get_db), _=Depends(require_hr)):
    q = db.query(Leave)
    if status:
        q = q.filter(Leave.status == status.upper())
    return q.order_by(Leave.created_at.desc()).all()


@router.patch("/leaves/{leave_id}/review")
def review_leave(leave_id: int, payload: LeaveReview, db: Session = Depends(get_db), hr=Depends(require_hr)):
    leave = db.query(Leave).filter(Leave.id == leave_id).first()
    if not leave: raise HTTPException(404, "Leave not found")
    if leave.status != LeaveStatusEnum.PENDING:
        raise HTTPException(400, "Leave already reviewed")
    leave.status      = payload.status
    leave.reviewed_by = hr.id
    leave.reviewed_at = datetime.utcnow()
    db.commit()
    _log(db, hr.id, f"Leave {leave_id} {payload.status}")
    return {"message": f"Leave {payload.status}"}


# ── PAYROLL ───────────────────────────────────────────────
@router.post("/payroll", response_model=PayrollOut)
def create_payroll(payload: PayrollCreate, db: Session = Depends(get_db), hr=Depends(require_hr)):
    emp = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if not emp: raise HTTPException(404, "Employee not found")
    existing = db.query(Payroll).filter(
        Payroll.employee_id == payload.employee_id,
        Payroll.month == payload.month, Payroll.year == payload.year
    ).first()
    if existing: raise HTTPException(400, "Payroll already exists for this month")
    net = payload.base_salary + payload.bonus - payload.deductions
    p = Payroll(
        employee_id=payload.employee_id, month=payload.month, year=payload.year,
        base_salary=payload.base_salary, bonus=payload.bonus,
        deductions=payload.deductions, net_salary=net
    )
    db.add(p); db.commit(); db.refresh(p)
    _log(db, hr.id, f"Created payroll for emp {payload.employee_id} {payload.month}/{payload.year}")
    return p


@router.post("/payroll/upload-excel")
async def upload_payroll_excel(
    month: int = Form(...), year: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db), hr=Depends(require_hr)
):
    content = await file.read()
    try:
        records = parse_payroll_excel(content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    created, skipped = 0, 0
    for r in records:
        emp_id = int(r["employee_id"])
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        if not emp: skipped += 1; continue
        existing = db.query(Payroll).filter(
            Payroll.employee_id == emp_id,
            Payroll.month == month, Payroll.year == year
        ).first()
        if existing: skipped += 1; continue
        p = Payroll(
            employee_id=emp_id, month=month, year=year,
            base_salary=r["base_salary"], bonus=r["bonus"],
            deductions=r["deductions"], net_salary=r["net_salary"]
        )
        db.add(p); created += 1
    db.commit()
    _log(db, hr.id, f"Payroll Excel uploaded {month}/{year}: {created} created")
    return {"created": created, "skipped": skipped}


@router.post("/payroll/{payroll_id}/mark-paid")
def mark_payroll_paid(payroll_id: int, db: Session = Depends(get_db), hr=Depends(require_hr)):
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p: raise HTTPException(404, "Payroll not found")
    p.status  = PayrollStatusEnum.PAID
    p.paid_at = datetime.utcnow()
    qr_path = generate_payroll_qr(
        p.employee.user.name, p.employee_id,
        p.month, p.year, p.net_salary, p.id
    )
    p.qr_code_path = qr_path
    db.commit()
    send_salary_slip(
        employee_email=p.employee.user.email,
        employee_name=p.employee.user.name,
        month_year=f"{p.month}/{p.year}",
        base=p.base_salary, bonus=p.bonus,
        deductions=p.deductions, net=p.net_salary,
        qr_code_path=qr_path
    )
    _log(db, hr.id, f"Payroll {payroll_id} marked PAID")
    return {"message": "Payroll paid and salary slip sent", "qr_code": qr_path}


@router.get("/payroll", response_model=List[PayrollOut])
def list_payroll(
    month: Optional[int] = None, year: Optional[int] = None,
    db: Session = Depends(get_db), _=Depends(require_hr)
):
    q = db.query(Payroll)
    if month: q = q.filter(Payroll.month == month)
    if year:  q = q.filter(Payroll.year  == year)
    return q.order_by(Payroll.created_at.desc()).all()


# ── BULK EMAIL ────────────────────────────────────────────
@router.post("/send-email")
async def send_email_endpoint(
    subject: str = Form(...),
    body: str = Form(...),
    department: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    hr=Depends(require_hr)
):
    q = db.query(Employee).join(User).filter(User.is_active == True)
    if department and department.lower() != "all":
        q = q.filter(Employee.department == department)
    employees  = q.all()
    recipients = [emp.user.email for emp in employees]
    if not recipients:
        raise HTTPException(400, "No recipients found")
    attachment_path = None
    if attachment:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        attachment_path = os.path.join(settings.UPLOAD_DIR, attachment.filename)
        with open(attachment_path, "wb") as f:
            shutil.copyfileobj(attachment.file, f)
    result = send_bulk_announcement(
        subject=subject, body=body,
        recipients=recipients, attachment_path=attachment_path
    )
    log = EmailLog(
        sender_id=hr.id, subject=subject, body=body,
        recipients=recipients, department=department,
        has_attachment=attachment_path
    )
    db.add(log); db.commit()
    _log(db, hr.id, f"Bulk email sent: '{subject}' to {len(recipients)} recipients")
    return {"message": f"Email sent to {result['success']} recipients", **result}


@router.get("/email-logs")
def hr_email_logs(db: Session = Depends(get_db), _=Depends(require_hr)):
    logs = db.query(EmailLog).order_by(EmailLog.sent_at.desc()).limit(30).all()
    return [{"id": l.id, "subject": l.subject, "count": len(l.recipients), "department": l.department, "sent_at": l.sent_at} for l in logs]


# ── HELPER ────────────────────────────────────────────────
def _log(db, user_id, action, detail=None):
    db.add(ActivityLog(user_id=user_id, action=action, detail=detail))
    db.commit()