from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()

# ==================
# User & Profiles
# ==================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    telegram_id = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)  # 'admin', 'client', 'model'
    status = Column(String, default="inactive")  # 'inactive', 'active', 'suspended', 'banned'
    created_at = Column(DateTime, default=datetime.utcnow)

    model_profile = relationship("ModelProfile", back_populates="user", uselist=False)
    client_profile = relationship("ClientProfile", back_populates="user", uselist=False)


class ModelProfile(Base):
    __tablename__ = "model_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    verification_status = Column(String, default="pending")  # 'pending', 'approved', 'rejected'
    approved_at = Column(DateTime)
    verification_photos = Column(Text)  # JSON list of photo URLs
    verification_video_file_id = Column(String)

    user = relationship("User", back_populates="model_profile")


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_spent = Column(Float, default=0.0)

    user = relationship("User", back_populates="client_profile")


# ==================
# Sessions & Transactions
# ==================
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    session_ref = Column(String, unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"))
    model_id = Column(Integer, ForeignKey("users.id"))
    session_type = Column(String)
    status = Column(String, default="pending")  # 'pending', 'active', 'completed', 'disputed'
    package_price = Column(Float)
    actual_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    transaction_ref = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    transaction_type = Column(String)  # 'platform_fee', 'booking_payment', etc.
    status = Column(String, default="pending")  # 'pending', 'completed', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class EscrowAccount(Base):
    __tablename__ = "escrow_accounts"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    amount = Column(Float)
    status = Column(String, default="held")  # 'held', 'released', 'disputed'
    dispute_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminAction(Base):
    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("users.id"))
    action_type = Column(String)
    target_user_id = Column(Integer, ForeignKey("users.id"))
    target_type = Column(String)
    target_id = Column(Integer)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

