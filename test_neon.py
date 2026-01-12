import asyncio
from sqlalchemy import text
from db import engine

async def test_connection():
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
