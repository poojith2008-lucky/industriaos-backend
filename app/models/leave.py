from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class LeaveStatusEnum(str, enum.Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class LeaveTypeEnum(str, enum.Enum):
    SICK    = "SICK"
    CASUAL  = "CASUAL"
    ANNUAL  = "ANNUAL"
    OTHER   = "OTHER"

class Leave(Base):
    __tablename__ = "leaves"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type  = Column(Enum(LeaveTypeEnum), nullable=False)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=False)
    days        = Column(Integer, nullable=False)
    reason      = Column(Text, nullable=True)
    status      = Column(Enum(LeaveStatusEnum), default=LeaveStatusEnum.PENDING)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="leaves")
    reviewer = relationship("User", foreign_keys=[reviewed_by])