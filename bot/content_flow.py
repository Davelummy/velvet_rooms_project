from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ContentPurchase, DigitalContent, User


def parse_content_args(text: str) -> Optional[dict]:
    if not text:
        return None

    parts = text.split("|", 1)
    left = parts[0].strip()
    description = parts[1].strip() if len(parts) > 1 else ""

    tokens = left.split()
    if len(tokens) < 3:
        return None

    content_type = tokens[0]
    try:
        price = float(tokens[1])
    except ValueError:
        return None

    title = " ".join(tokens[2:]).strip()
    if not title:
        return None

    return {
        "content_type": content_type,
        "price": price,
        "title": title,
        "description": description,
    }


async def create_content(
    db: AsyncSession,
    model: User,
    content_type: str,
    price: float,
    title: str,
    description: str,
    telegram_file_id: Optional[str] = None,
    preview_file_id: Optional[str] = None,
) -> DigitalContent:
    content = DigitalContent(
        model_id=model.id,
        content_type=content_type,
        title=title,
        description=description,
        price=price,
        telegram_file_id=telegram_file_id,
        preview_file_id=preview_file_id,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return content


async def list_active_content(db: AsyncSession) -> List[DigitalContent]:
    result = await db.execute(
        select(DigitalContent).where(DigitalContent.is_active.is_(True)).order_by(DigitalContent.id)
    )
    return list(result.scalars().all())


async def list_model_content(db: AsyncSession, model_id: int) -> List[DigitalContent]:
    result = await db.execute(
        select(DigitalContent).where(DigitalContent.model_id == model_id).order_by(DigitalContent.id)
    )
    return list(result.scalars().all())


async def get_content_by_id(db: AsyncSession, content_id: int) -> Optional[DigitalContent]:
    result = await db.execute(select(DigitalContent).where(DigitalContent.id == content_id))
    return result.scalar_one_or_none()


async def create_purchase(
    db: AsyncSession,
    content: DigitalContent,
    client: User,
) -> ContentPurchase:
    purchase = ContentPurchase(
        content_id=content.id,
        client_id=client.id,
        price_paid=content.price,
    )
    db.add(purchase)

    content.total_sales += 1
    content.total_revenue += content.price or 0

    await db.commit()
    await db.refresh(purchase)
    return purchase
