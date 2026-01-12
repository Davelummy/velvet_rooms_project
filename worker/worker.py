import asyncio


async def background_worker():
    while True:
        print("Worker running...")
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(background_worker())
