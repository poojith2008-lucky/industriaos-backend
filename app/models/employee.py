from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    department        = Column(String(100), nullable=False)
    position          = Column(String(100), nullable=False)
    base_salary       = Column(Float, nullable=False, default=0.0)
    phone             = Column(String(20), nullable=True)
    address           = Column(String(255), nullable=True)
    emergency_contact = Column(String(20), nullable=True)
    profile_picture   = Column(String(255), nullable=True)
    join_date         = Column(Date, default=datetime.utcnow)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    user     = relationship("User", back_populates="employee")
    leaves   = relationship("Leave", back_populates="employee")
    payrolls = relationship("Payroll", back_populates="employee")