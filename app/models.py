from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)  # telegram user id
    username = Column(String(255), nullable=True)
    language = Column(String(10), default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    tariff_code = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=True)
    hash = Column(Text, nullable=True)
    photo_file_id = Column(String(300), nullable=True)
    doc_file_id = Column(String(300), nullable=True)
    status = Column(String(50), default="pending")  # pending / confirmed / rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    admin_id = Column(BigInteger, nullable=True)

    user = relationship("User", back_populates="payments")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    tariff_code = Column(String(50), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")