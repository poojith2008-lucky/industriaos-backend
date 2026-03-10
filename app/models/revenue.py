from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Revenue(Base):
    __tablename__ = "revenues"

    id          = Column(Integer, primary_key=True, index=True)
    month       = Column(Integer, nullable=False)
    year        = Column(Integer, nullable=False)
    amount      = Column(Float, nullable=False)
    expense     = Column(Float, nullable=False, default=0.0)
    profit      = Column(Float, nullable=False, default=0.0)
    notes       = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User", foreign_keys=[uploaded_by])


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    action     = Column(String(255), nullable=False)
    detail     = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activity_logs")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id             = Column(Integer, primary_key=True, index=True)
    sender_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject        = Column(String(255), nullable=False)
    body           = Column(Text, nullable=False)
    recipients     = Column(JSON, nullable=False)
    department     = Column(String(100), nullable=True)
    has_attachment = Column(String(255), nullable=True)
    sent_at        = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", back_populates="email_logs")