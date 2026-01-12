from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from typing import Optional, List

from redis.asyncio import Redis
from sqlalchemy import select
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

from config import settings
from db import AsyncSessionLocal
from models import AdminAction, ClientProfile, EscrowAccount, ModelProfile, User
from content_flow import (
    create_content,
    create_purchase,
    get_content_by_id,
    list_active_content,
    list_model_content,
    parse_content_args,
)
from session_flow import (
    create_session_with_escrow,
    get_or_create_user,
    get_session_by_ref,
    get_user_by_telegram_id,
    set_escrow_status,
    set_session_status,
    update_user_role,
)

WEBHOOK_PATH = "/webhook"
ADMIN_WEBHOOK_PATH = "/admin_webhook"

redis_client: Optional[Redis] = None
PENDING_REGISTRATIONS: dict[int, dict[str, str]] = {}


def _require_bot_token() -> str:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    return settings.bot_token


def _require_webhook_base_url() -> str:
    if not settings.webhook_base_url:
        raise RuntimeError("WEBHOOK_BASE_URL is required for webhook mode")
    return settings.webhook_base_url.rstrip("/")


def _init_sentry():
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[AioHttpIntegration()],
            traces_sample_rate=0.1,
        )


async def init_redis():
    global redis_client
    if settings.redis_url:
        redis_client = Redis.from_url(settings.redis_url)


async def close_redis():
    if redis_client is not None:
        await redis_client.close()


async def start_handler(message: types.Message):
    async with AsyncSessionLocal() as db:
        await get_or_create_user(
            db=db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role="unassigned",
        )

    await message.answer(
        "Welcome to Velvet Rooms 👋\n"
        "Choose your role to continue (you can switch later):",
        reply_markup=_role_selection_keyboard(),
    )


def _is_admin(user_id: Optional[int]) -> bool:
    return user_id is not None and user_id in settings.admin_telegram_ids


def _role_selection_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🧑‍💼 I'm a Client", callback_data="role:client"),
            InlineKeyboardButton(text="✨ I'm a Model", callback_data="role:model"),
        ]
    ]
    rows.append([InlineKeyboardButton(text="ℹ️ Learn More", callback_data="menu:learn_more")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _client_onboarding_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✅ Register as Client", callback_data="register:client")],
        [InlineKeyboardButton(text="🖼️ Browse Content", callback_data="action:list_content")],
        [InlineKeyboardButton(text="📘 How it works", callback_data="info:client")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="menu:role_select")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _model_onboarding_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✅ Register as Model", callback_data="register:model")],
        [InlineKeyboardButton(text="➕ Add Content", callback_data="action:add_content")],
        [InlineKeyboardButton(text="📘 How it works", callback_data="info:model")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="menu:role_select")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _client_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🖼️ Browse Content", callback_data="action:list_content"),
            InlineKeyboardButton(text="💳 Buy Content", callback_data="action:buy_content"),
        ],
        [
            InlineKeyboardButton(text="📅 Book Session", callback_data="action:create_session"),
            InlineKeyboardButton(text="⚠️ Dispute Session", callback_data="action:dispute_session"),
        ],
        [
            InlineKeyboardButton(text="✨ Switch to Model", callback_data="role:model"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _model_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="➕ Add Content", callback_data="action:add_content"),
            InlineKeyboardButton(text="📂 My Content", callback_data="action:my_content"),
        ],
        [
            InlineKeyboardButton(text="▶️ Start Session", callback_data="action:start_session"),
            InlineKeyboardButton(text="✅ End Session", callback_data="action:end_session"),
        ],
        [
            InlineKeyboardButton(text="🧑‍💼 Switch to Client", callback_data="role:client"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Release Escrow", callback_data="admin:release_escrow")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="admin:home")],
        ]
    )


async def _send_role_menu(message: types.Message, role: str):
    if role == "model":
        keyboard = _model_menu_keyboard()
        text = (
            "Model dashboard ✨\n"
            "You are all set. Choose what to do next."
        )
    else:
        keyboard = _client_menu_keyboard()
        text = (
            "Client dashboard 🧑‍💼\n"
            "You are all set. Choose what to do next."
        )
    await message.answer(text, reply_markup=keyboard)


async def _send_onboarding_dashboard(message: types.Message, role: str) -> None:
    if role == "client":
        await message.answer(
            "Client onboarding 🧑‍💼\n"
            "Register to unlock bookings and purchases.\n\n"
            "What you'll get:\n"
            "• Access to premium content\n"
            "• Direct session booking\n"
            "• Protected dispute flow\n\n"
            "Step 1: Tap register below.",
            reply_markup=_client_onboarding_keyboard(),
        )
        return

    if role == "model":
        await message.answer(
            "Model onboarding ✨\n"
            "Register to start earning.\n\n"
            "What you'll get:\n"
            "• Sell content with previews\n"
            "• Run sessions end-to-end\n"
            "• Track your catalog & revenue\n\n"
            "Step 1: Tap register below.",
            reply_markup=_model_onboarding_keyboard(),
        )
        return


def _admin_webhook_base_url() -> str:
    return (settings.admin_bot_webhook_base_url or settings.webhook_base_url or "").rstrip("/")


async def _get_user_or_prompt_role(
    message: types.Message, user_id: int
) -> Optional[User]:
    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, user_id)
        if not user:
            user = await get_or_create_user(
                db=db,
                telegram_id=user_id,
                username=message.from_user.username if message.from_user else None,
                first_name=message.from_user.first_name if message.from_user else None,
                last_name=message.from_user.last_name if message.from_user else None,
                role="unassigned",
            )
    if user.role == "unassigned":
        await message.answer(
            "Please choose your role to continue:",
            reply_markup=_role_selection_keyboard(),
        )
        return None
    return user


async def _require_role_from_user_id(
    message: types.Message, user_id: int, role: str
) -> Optional[User]:
    user = await _get_user_or_prompt_role(message, user_id)
    if not user:
        return None
    if user.role != role:
        await message.answer(f"{role.title()} access required. Use /register_{role}.")
        return None
    return user


async def _require_role(message: types.Message, role: str) -> Optional[User]:
    if not message.from_user:
        await message.answer("Unable to identify user. Please try again.")
        return None
    return await _require_role_from_user_id(message, message.from_user.id, role)


async def register_model(message: types.Message):
    if not message.from_user:
        await message.answer("Unable to identify user. Please try again.")
        return
    await _start_registration_flow(message, message.from_user.id, "model")


async def register_client(message: types.Message):
    if not message.from_user:
        await message.answer("Unable to identify user. Please try again.")
        return
    await _start_registration_flow(message, message.from_user.id, "client")


async def menu_handler(message: types.Message):
    await message.answer(
        "Choose your role to continue:",
        reply_markup=_role_selection_keyboard(),
    )


async def _handle_role_selection(query: CallbackQuery, role: str):
    await query.answer()
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(
            db=db,
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            first_name=query.from_user.first_name,
            last_name=query.from_user.last_name,
            role="unassigned",
        )

    if user.role == role:
        await _send_role_menu(query.message, role)
        return

    await _send_onboarding_dashboard(query.message, role)


async def _handle_register_selection(query: CallbackQuery, role: str):
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(
            db=db,
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            first_name=query.from_user.first_name,
            last_name=query.from_user.last_name,
            role="unassigned",
        )
        if user.role != "unassigned" and user.role != role:
            await query.answer("You already registered in another role.")
            return

        await query.answer()
        await _start_registration_flow(query.message, query.from_user.id, role)


async def _start_registration_flow(message: types.Message, user_id: int, role: str):
    PENDING_REGISTRATIONS[user_id] = {"role": role, "step": "email"}
    await message.answer(
        "Please send your email to complete registration.",
    )


async def _send_usage(message: types.Message, text: str):
    await message.answer(text)


def _looks_like_email(value: str) -> bool:
    return "@" in value and "." in value


async def registration_input_handler(message: types.Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    if user_id not in PENDING_REGISTRATIONS:
        return
    if not message.text:
        await message.answer("Please send text for registration.")
        return
    if message.text.strip().startswith("/"):
        await message.answer("Please finish registration before using commands.")
        return

    state = PENDING_REGISTRATIONS[user_id]
    role = state["role"]
    step = state["step"]
    text = message.text.strip()

    if step == "email":
        if not _looks_like_email(text):
            await message.answer("That doesn't look like a valid email. Try again.")
            return

        async with AsyncSessionLocal() as db:
            user = await get_or_create_user(
                db=db,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                role="unassigned",
            )
            user.email = text
            await db.commit()
            await db.refresh(user)

            if role == "model":
                state["step"] = "display_name"
                await message.answer("Great! Send your display name.")
                return

            await update_user_role(db, user, "client")
            profile = await db.execute(
                select(ClientProfile).where(ClientProfile.user_id == user.id)
            )
            if not profile.scalar_one_or_none():
                db.add(ClientProfile(user_id=user.id))
                await db.commit()
            PENDING_REGISTRATIONS.pop(user_id, None)

        await message.answer("Client registration complete ✅")
        await _send_role_menu(message, "client")
        return

    if step == "display_name":
        if len(text) < 2:
            await message.answer("Display name is too short. Try again.")
            return
        async with AsyncSessionLocal() as db:
            user = await get_or_create_user(
                db=db,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                role="unassigned",
            )
            await update_user_role(db, user, "model")
            profile = await db.execute(
                select(ModelProfile).where(ModelProfile.user_id == user.id)
            )
            model_profile = profile.scalar_one_or_none()
            if not model_profile:
                model_profile = ModelProfile(
                    user_id=user.id,
                    display_name=text,
                )
                db.add(model_profile)
                await db.commit()
            else:
                model_profile.display_name = text
                await db.commit()

            PENDING_REGISTRATIONS.pop(user_id, None)

        await message.answer("Model registration complete ✅")
        await _send_role_menu(message, "model")
        return


async def callback_handler(query: CallbackQuery):
    data = query.data or ""
    if data.startswith("role:"):
        role = data.split(":", 1)[1]
        await _handle_role_selection(query, role)
        return

    if data.startswith("register:"):
        role = data.split(":", 1)[1]
        await _handle_register_selection(query, role)
        return

    if data == "menu:role_select":
        await query.answer()
        await query.message.answer(
            "Choose your role to continue:",
            reply_markup=_role_selection_keyboard(),
        )
        return

    if data == "menu:learn_more":
        await query.answer()
        await query.message.answer(
            "Velvet Rooms is a curated space for premium sessions and content.\n\n"
            "Clients:\n"
            "• Discover premium content\n"
            "• Book sessions securely\n\n"
            "Models:\n"
            "• Sell content\n"
            "• Run sessions end-to-end",
            reply_markup=_role_selection_keyboard(),
        )
        return

    if data == "info:client":
        await query.answer()
        await query.message.answer(
            "Client guide 🧑‍💼\n"
            "1) Register as a client\n"
            "2) Browse content or book a session\n"
            "3) Pay and enjoy your experience\n\n"
            "Need help? Use /menu to return.",
            reply_markup=_client_onboarding_keyboard(),
        )
        return

    if data == "info:model":
        await query.answer()
        await query.message.answer(
            "Model guide ✨\n"
            "1) Register as a model\n"
            "2) Add content to your catalog\n"
            "3) Start and complete sessions\n\n"
            "Need help? Use /menu to return.",
            reply_markup=_model_onboarding_keyboard(),
        )
        return

    if data == "menu:main":
        await query.answer()
        await query.message.answer(
            "Choose your role to continue:",
            reply_markup=_role_selection_keyboard(),
        )
        return

    if data == "action:list_content":
        await query.answer()
        await list_content_handler(query.message)
        return

    if data == "action:my_content":
        await query.answer()
        await _send_my_content(query.message, query.from_user.id)
        return

    if data == "action:add_content":
        await query.answer()
        await _send_usage(
            query.message,
            "Usage: /add_content <type> <price> <title> | <description>",
        )
        return

    if data == "action:buy_content":
        await query.answer()
        await _send_usage(query.message, "Usage: /buy_content <content_id>")
        return

    if data == "action:create_session":
        await query.answer()
        await _send_usage(
            query.message,
            "Usage: /create_session <model_telegram_id> <type> <price>",
        )
        return

    if data == "action:start_session":
        await query.answer()
        await _send_usage(query.message, "Usage: /start_session <session_ref>")
        return

    if data == "action:end_session":
        await query.answer()
        await _send_usage(query.message, "Usage: /end_session <session_ref>")
        return

    if data == "action:dispute_session":
        await query.answer()
        await _send_usage(
            query.message,
            "Usage: /dispute_session <session_ref> <reason>",
        )
        return


async def admin_start_handler(message: types.Message):
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Admin access required.")
        return
    await message.answer("Admin dashboard 🛡️", reply_markup=_admin_menu_keyboard())


async def admin_release_escrow_handler(message: types.Message):
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Admin access required.")
        return

    args = _parse_args(message)
    if len(args) < 1:
        await message.answer("Usage: /release_escrow <session_ref>")
        return

    session_ref = args[0]
    async with AsyncSessionLocal() as db:
        session = await get_session_by_ref(db, session_ref)
        if not session:
            await message.answer("Session not found.")
            return

        result = await db.execute(
            select(EscrowAccount).where(EscrowAccount.session_id == session.id)
        )
        escrow_obj = result.scalar_one_or_none()
        if not escrow_obj:
            await message.answer("Escrow record not found.")
            return

        await set_escrow_status(db, escrow_obj, "released")
        db.add(
            AdminAction(
                admin_id=message.from_user.id,
                action_type="release_escrow",
                target_user_id=session.model_id,
                target_type="session",
                target_id=session.id,
                details={"session_ref": session_ref},
            )
        )
        await db.commit()
        await message.answer(f"Escrow released for {session_ref}.")
        if settings.escrow_log_channel_id:
            await message.bot.send_message(
                settings.escrow_log_channel_id,
                f"Escrow released for session {session_ref} by admin {message.from_user.id}",
            )


async def admin_callback_handler(query: CallbackQuery):
    if not _is_admin(query.from_user.id):
        await query.answer("Admin access required.", show_alert=True)
        return
    data = query.data or ""
    if data == "admin:release_escrow":
        await query.answer()
        await query.message.answer("Usage: /release_escrow <session_ref>")
        return
    if data == "admin:home":
        await query.answer()
        await query.message.answer("Admin dashboard 🛡️", reply_markup=_admin_menu_keyboard())
        return



def _parse_args(message: types.Message) -> List[str]:
    if not message.text:
        return []
    return message.text.strip().split()[1:]


async def create_session_handler(message: types.Message):
    user = await _require_role(message, "client")
    if not user:
        return

    args = _parse_args(message)
    if len(args) < 3:
        await message.answer("Usage: /create_session <model_telegram_id> <type> <price>")
        return

    try:
        model_telegram_id = int(args[0])
        session_type = args[1]
        price = float(args[2])
    except ValueError:
        await message.answer("Invalid arguments. Example: /create_session 123456 video 50")
        return

    async with AsyncSessionLocal() as db:
        client = await get_or_create_user(
            db=db,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role="client",
        )
        model = await get_user_by_telegram_id(db, model_telegram_id)
        if not model or model.role != "model":
            await message.answer("Model not found or not registered as model.")
            return

        session = await create_session_with_escrow(db, client, model, session_type, price)
        await message.answer(
            f"Session created: {session.session_ref}\n"
            f"Status: {session.status}\n"
            "Escrow: held"
        )


async def start_session_handler(message: types.Message):
    user = await _require_role(message, "model")
    if not user:
        return

    args = _parse_args(message)
    if len(args) < 1:
        await message.answer("Usage: /start_session <session_ref>")
        return

    session_ref = args[0]
    async with AsyncSessionLocal() as db:
        session = await get_session_by_ref(db, session_ref)
        if not session:
            await message.answer("Session not found.")
            return

        user = await get_user_by_telegram_id(db, message.from_user.id)
        if not user or user.id != session.model_id:
            await message.answer("Only the model can start the session.")
            return

        await set_session_status(db, session, "active")
        await message.answer(f"Session {session_ref} started.")


async def end_session_handler(message: types.Message):
    user = await _require_role(message, "model")
    if not user:
        return

    args = _parse_args(message)
    if len(args) < 1:
        await message.answer("Usage: /end_session <session_ref>")
        return

    session_ref = args[0]
    async with AsyncSessionLocal() as db:
        session = await get_session_by_ref(db, session_ref)
        if not session:
            await message.answer("Session not found.")
            return

        user = await get_user_by_telegram_id(db, message.from_user.id)
        if not user or user.id != session.model_id:
            await message.answer("Only the model can end the session.")
            return

        await set_session_status(db, session, "completed")
        await message.answer(f"Session {session_ref} completed. Awaiting escrow release.")


async def dispute_session_handler(message: types.Message):
    user = await _get_user_or_prompt_role(message, message.from_user.id)
    if not user:
        return

    args = _parse_args(message)
    if len(args) < 2:
        await message.answer("Usage: /dispute_session <session_ref> <reason>")
        return

    session_ref = args[0]
    reason = " ".join(args[1:])
    async with AsyncSessionLocal() as db:
        session = await get_session_by_ref(db, session_ref)
        if not session:
            await message.answer("Session not found.")
            return

        user = await get_user_by_telegram_id(db, message.from_user.id)
        if not user or user.id not in {session.client_id, session.model_id}:
            await message.answer("Only participants can dispute a session.")
            return

        result = await db.execute(
            select(EscrowAccount).where(EscrowAccount.session_id == session.id)
        )
        escrow_obj = result.scalar_one_or_none()
        if not escrow_obj:
            await message.answer("Escrow record not found.")
            return

        await set_session_status(db, session, "disputed")
        await set_escrow_status(db, escrow_obj, "disputed", reason=reason)
        await message.answer(f"Session {session_ref} disputed: {reason}")
        if settings.escrow_log_channel_id:
            await message.bot.send_message(
                settings.escrow_log_channel_id,
                f"Dispute opened for session {session_ref} by user {message.from_user.id}: {reason}",
            )


async def add_content_handler(message: types.Message):
    user = await _require_role(message, "model")
    if not user:
        return

    parsed = parse_content_args(message.text or "")
    if not parsed:
        await message.answer(
            "Usage: /add_content <type> <price> <title> | <description>"
        )
        return

    async with AsyncSessionLocal() as db:
        content = await create_content(
            db=db,
            model=user,
            content_type=parsed["content_type"],
            price=parsed["price"],
            title=parsed["title"],
            description=parsed["description"],
        )
        await message.answer(
            f"Content created: #{content.id} - {content.title} (${content.price})"
        )
        if settings.model_dashboard_channel_id:
            await message.bot.send_message(
                settings.model_dashboard_channel_id,
                f"New content by @{message.from_user.username or message.from_user.id}:\n"
                f"#{content.id} {content.title} - ${content.price}\n"
                f"{content.description}",
            )
        if settings.main_gallery_channel_id:
            await message.bot.send_message(
                settings.main_gallery_channel_id,
                f"New content drop:\n"
                f"{content.title} - ${content.price}\n"
                f"{content.description}\n"
                f"Use /buy_content {content.id} to purchase.",
            )


async def list_content_handler(message: types.Message):
    async with AsyncSessionLocal() as db:
        content_list = await list_active_content(db)
        if not content_list:
            await message.answer("No content available.")
            return

        lines = ["Available content:"]
        for item in content_list[:20]:
            lines.append(f"#{item.id} {item.title} - ${item.price}")
        await message.answer("\n".join(lines))


async def _send_my_content(message: types.Message, user_id: int):
    async with AsyncSessionLocal() as db:
        user = await _require_role_from_user_id(message, user_id, "model")
        if not user:
            return

        content_list = await list_model_content(db, user.id)
        if not content_list:
            await message.answer("You have no content yet.")
            return

        lines = ["Your content:"]
        for item in content_list[:20]:
            lines.append(f"#{item.id} {item.title} - ${item.price}")
        await message.answer("\n".join(lines))


async def my_content_handler(message: types.Message):
    if not message.from_user:
        await message.answer("Unable to identify user. Please try again.")
        return
    await _send_my_content(message, message.from_user.id)


async def buy_content_handler(message: types.Message):
    user = await _require_role(message, "client")
    if not user:
        return

    args = _parse_args(message)
    if len(args) < 1:
        await message.answer("Usage: /buy_content <content_id>")
        return

    try:
        content_id = int(args[0])
    except ValueError:
        await message.answer("Invalid content id.")
        return

    async with AsyncSessionLocal() as db:
        content = await get_content_by_id(db, content_id)
        if not content or not content.is_active:
            await message.answer("Content not found or inactive.")
            return

        await create_purchase(db, content, user)
        await message.answer(f"Purchase recorded for content #{content_id}.")


async def on_startup(bot: Bot):
    await init_redis()
    webhook_url = f"{_require_webhook_base_url()}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await close_redis()
    await bot.session.close()


def main():
    _init_sentry()

    bot = Bot(token=_require_bot_token())
    dp = Dispatcher()

    admin_bot = None
    admin_dp = None
    if settings.admin_bot_token:
        admin_bot = Bot(token=settings.admin_bot_token)
        admin_dp = Dispatcher()

    dp.message.register(start_handler, Command("start"))
    dp.message.register(menu_handler, Command("menu"))
    dp.message.register(register_model, Command("register_model"))
    dp.message.register(register_client, Command("register_client"))
    dp.message.register(create_session_handler, Command("create_session"))
    dp.message.register(start_session_handler, Command("start_session"))
    dp.message.register(end_session_handler, Command("end_session"))
    dp.message.register(dispute_session_handler, Command("dispute_session"))
    dp.message.register(add_content_handler, Command("add_content"))
    dp.message.register(list_content_handler, Command("list_content"))
    dp.message.register(my_content_handler, Command("my_content"))
    dp.message.register(buy_content_handler, Command("buy_content"))
    dp.callback_query.register(callback_handler)
    dp.message.register(registration_input_handler)

    if admin_dp and admin_bot:
        admin_dp.message.register(admin_start_handler, Command("start"))
        admin_dp.message.register(admin_release_escrow_handler, Command("release_escrow"))
        admin_dp.callback_query.register(admin_callback_handler)

    async def handle_startup(app: web.Application):
        await on_startup(bot)
        if admin_bot:
            admin_webhook_base = _admin_webhook_base_url()
            if not admin_webhook_base:
                raise RuntimeError("ADMIN_BOT_WEBHOOK_BASE_URL is required")
            await admin_bot.set_webhook(
                f"{admin_webhook_base}{ADMIN_WEBHOOK_PATH}",
                drop_pending_updates=True,
            )

    async def handle_shutdown(app: web.Application):
        await on_shutdown(bot)
        if admin_bot:
            await admin_bot.delete_webhook()
            await admin_bot.session.close()

    app = web.Application()
    app.on_startup.append(handle_startup)
    app.on_shutdown.append(handle_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    if admin_bot and admin_dp:
        SimpleRequestHandler(dispatcher=admin_dp, bot=admin_bot).register(
            app, path=ADMIN_WEBHOOK_PATH
        )
    setup_application(app, dp, bot=bot)
    if admin_bot and admin_dp:
        setup_application(app, admin_dp, bot=admin_bot)

    web.run_app(app, host=settings.webhook_host, port=settings.webhook_port)


if __name__ == "__main__":
    main()
