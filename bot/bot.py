import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as aioredis  # modern async redis

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# ---------------------------
# DATABASE SETUP
# ---------------------------
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ---------------------------
# REDIS SETUP
# ---------------------------
redis_client = None

async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(REDIS_URL)

# ---------------------------
# TELEGRAM HANDLERS
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}! 🎉\n"
        "Welcome to Velvet Rooms.\n"
        "Your bot is running successfully."
    )

async def approve_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Approve model logic placeholder.")

async def reject_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reject model logic placeholder.")

# ---------------------------
# MAIN
# ---------------------------
async def main():
    # Initialize Redis
    await init_redis()

    # Build the bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve_model))
    app.add_handler(CommandHandler("reject", reject_model))

    # Run the bot (PTB handles the asyncio loop)
    await app.run_polling()

# ---------------------------
# ENTRY POINT
# ---------------------------
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
