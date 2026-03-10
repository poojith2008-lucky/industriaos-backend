from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from app.models.user import RoleEnum
from app.models.leave import LeaveStatusEnum, LeaveTypeEnum
from app.models.payroll import PayrollStatusEnum

# ── USER ──────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum

class UserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: RoleEnum
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

# ── EMPLOYEE ──────────────────────────────────────────────
class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    department: str
    position: str
    base_salary: float
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    join_date: Optional[date] = None

class EmployeeUpdate(BaseModel):
    department: Optional[str] = None
    position: Optional[str] = None
    base_salary: Optional[float] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class EmployeeOut(BaseModel):
    id: int
    user_id: int
    department: str
    position: str
    base_salary: float
    phone: Optional[str]
    address: Optional[str]
    emergency_contact: Optional[str]
    profile_picture: Optional[str]
    join_date: Optional[date]
    user: UserOut
    class Config:
        from_attributes = True

# ── LEAVE ─────────────────────────────────────────────────
class LeaveCreate(BaseModel):
    leave_type: LeaveTypeEnum
    start_date: date
    end_date: date
    reason: Optional[str] = None

class LeaveReview(BaseModel):
    status: LeaveStatusEnum

class LeaveOut(BaseModel):
    id: int
    employee_id: int
    leave_type: LeaveTypeEnum
    start_date: date
    end_date: date
    days: int
    reason: Optional[str]
    status: LeaveStatusEnum
    created_at: datetime
    class Config:
        from_attributes = True

# ── PAYROLL ───────────────────────────────────────────────
class PayrollCreate(BaseModel):
    employee_id: int
    month: int
    year: int
    base_salary: float
    bonus: float = 0.0
    deductions: float = 0.0

class PayrollOut(BaseModel):
    id: int
    employee_id: int
    month: int
    year: int
    base_salary: float
    bonus: float
    deductions: float
    net_salary: float
    status: PayrollStatusEnum
    qr_code_path: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True

# ── REVENUE ───────────────────────────────────────────────
class RevenueCreate(BaseModel):
    month: int
    year: int
    amount: float
    expense: float
    notes: Optional[str] = None

class RevenueOut(BaseModel):
    id: int
    month: int
    year: int
    amount: float
    expense: float
    profit: float
    notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

# ── EMAIL ─────────────────────────────────────────────────
class EmailSend(BaseModel):
    subject: str
    body: str
    department: Optional[str] = None
    recipient_emails: Optional[List[EmailStr]] = None

class EmailLogOut(BaseModel):
    id: int
    subject: str
    recipients: List[str]
    department: Optional[str]
    sent_at: datetime
    class Config:
        from_attributes = True

# ── ACTIVITY LOG ──────────────────────────────────────────
class ActivityLogOut(BaseModel):
    id: int
    action: str
    detail: Optional[str]
    created_at: datetime
    user: UserOut
    class Config:
        from_attributes = True