import secrets
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Session, EscrowAccount


def generate_session_ref() -> str:
    return f"sess_{secrets.token_hex(4)}"


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    role: str,
) -> User:
    user = await get_user_by_telegram_id(db, telegram_id)
    if user:
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_role(db: AsyncSession, user: User, role: str) -> User:
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def create_session_with_escrow(
    db: AsyncSession,
    client: User,
    model: User,
    session_type: str,
    price: float,
) -> Session:
    session_ref = generate_session_ref()
    session = Session(
        session_ref=session_ref,
        client_id=client.id,
        model_id=model.id,
        session_type=session_type,
        package_price=price,
        status="pending",
    )
    db.add(session)
    await db.flush()

    escrow = EscrowAccount(
        session_id=session.id,
        amount=price,
        status="held",
    )
    db.add(escrow)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_by_ref(db: AsyncSession, session_ref: str) -> Optional[Session]:
    result = await db.execute(select(Session).where(Session.session_ref == session_ref))
    return result.scalar_one_or_none()


async def set_session_status(db: AsyncSession, session: Session, status: str):
    session.status = status
    await db.commit()
    await db.refresh(session)


async def set_escrow_status(
    db: AsyncSession,
    escrow: EscrowAccount,
    status: str,
    reason: Optional[str] = None,
):
    escrow.status = status
    if reason is not None:
        escrow.dispute_reason = reason
    await db.commit()
    await db.refresh(escrow)


async def get_escrow_for_session(db: AsyncSession, session_id: int) -> Optional[EscrowAccount]:
    result = await db.execute(select(EscrowAccount).where(EscrowAccount.session_id == session_id))
    return result.scalar_one_or_none()
