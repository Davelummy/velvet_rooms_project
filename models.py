from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    role = Column(String, nullable=False)
    status = Column(String, default="inactive")
    wallet_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    model_profile = relationship("ModelProfile", back_populates="user", uselist=False)
    client_profile = relationship("ClientProfile", back_populates="user", uselist=False)


class ModelProfile(Base):
    __tablename__ = "model_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    display_name = Column(String)
    verification_status = Column(String, default="pending")
    approved_at = Column(DateTime)
    approved_by = Column(Integer)
    verification_photos = Column(ARRAY(Text))
    verification_video_file_id = Column(String)
    total_earnings = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="model_profile")


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_spent = Column(Float, default=0.0)

    user = relationship("User", back_populates="client_profile")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    session_ref = Column(String, unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_type = Column(String)
    package_price = Column(Float)
    status = Column(String, default="pending")
    actual_start = Column(DateTime)
    scheduled_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class DigitalContent(Base):
    __tablename__ = "digital_content"

    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content_type = Column(String)
    title = Column(String)
    description = Column(Text)
    price = Column(Float)
    telegram_file_id = Column(String)
    preview_file_id = Column(String)
    is_active = Column(Boolean, default=True)
    total_sales = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContentPurchase(Base):
    __tablename__ = "content_purchases"

    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey("digital_content.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(Integer)
    price_paid = Column(Float)
    purchased_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    transaction_ref = Column(String, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(String)
    amount = Column(Float)
    payment_provider = Column(String)
    status = Column(String)
    metadata_json = Column(JSONB)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class EscrowAccount(Base):
    __tablename__ = "escrow_accounts"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    amount = Column(Float)
    status = Column(String, default="held")
    dispute_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminAction(Base):
    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String)
    target_user_id = Column(Integer, ForeignKey("users.id"))
    target_type = Column(String)
    target_id = Column(Integer)
    details = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
