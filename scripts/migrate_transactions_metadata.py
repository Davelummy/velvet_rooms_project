import asyncio
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from config import settings  # noqa: E402


async def main():
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")

    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='transactions'"
                )
            )
            columns = {row[0] for row in result.fetchall()}
            if "metadata" in columns and "metadata_json" not in columns:
                await conn.execute(
                    text("ALTER TABLE transactions RENAME COLUMN metadata TO metadata_json")
                )
                print("✅ Renamed transactions.metadata -> transactions.metadata_json")
            else:
                print("No rename needed.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
