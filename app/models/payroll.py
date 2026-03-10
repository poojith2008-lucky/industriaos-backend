from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class PayrollStatusEnum(str, enum.Enum):
    PENDING   = "PENDING"
    PROCESSED = "PROCESSED"
    PAID      = "PAID"

class Payroll(Base):
    __tablename__ = "payrolls"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month        = Column(Integer, nullable=False)
    year         = Column(Integer, nullable=False)
    base_salary  = Column(Float, nullable=False)
    bonus        = Column(Float, default=0.0)
    deductions   = Column(Float, default=0.0)
    net_salary   = Column(Float, nullable=False)
    status       = Column(Enum(PayrollStatusEnum), default=PayrollStatusEnum.PENDING)
    qr_code_path = Column(String(255), nullable=True)
    paid_at      = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = relationship("Employee", back_populates="payrolls")