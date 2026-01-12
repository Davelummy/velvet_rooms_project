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
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='users' AND column_name='telegram_id'"
                )
            )
            row = result.fetchone()
            if not row:
                raise RuntimeError("users.telegram_id column not found")

            data_type = row[0]
            if data_type == "bigint":
                print("users.telegram_id already bigint.")
                return

            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ALTER COLUMN telegram_id TYPE BIGINT "
                    "USING telegram_id::bigint"
                )
            )
            print("✅ Migrated users.telegram_id to BIGINT")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
