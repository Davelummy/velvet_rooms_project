import asyncio
import os
from redis.asyncio import Redis
from dotenv import load_dotenv

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def main():
    redis = Redis.from_url(REDIS_URL)
    
    # Test setting a value
    await redis.set("test_key", "Hello Redis!")
    
    # Get value (manual decode)
    value = await redis.get("test_key")
    if value is not None:
        value = value.decode("utf-8")
    
    print("✅ Redis Test Value:", value)
    
    await redis.close()

asyncio.run(main())

