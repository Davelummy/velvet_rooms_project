import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text  # <-- import this
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def test_connection():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env")
        return

    engine = create_async_engine(DATABASE_URL, echo=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT NOW()"))
            row = result.fetchone()
            print("✅ Connected! Current time:", row[0])
    except Exception as e:
        print("❌ Connection failed:", e)
    finally:
        await engine.dispose()

asyncio.run(test_connection())

