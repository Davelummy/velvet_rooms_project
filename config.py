import os
from dataclasses import dataclass
from typing import Optional, Tuple, List
from dotenv import load_dotenv

load_dotenv()


def _get_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _get_int_list(value: Optional[str]) -> List[int]:
    if not value:
        return []
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def _get_int_with_default(value: Optional[str], default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    bot_token: Optional[str] = os.getenv("BOT_TOKEN")
    admin_bot_token: Optional[str] = os.getenv("ADMIN_BOT_TOKEN")
    database_url: Optional[str] = os.getenv("DATABASE_URL")
    redis_url: Optional[str] = os.getenv("REDIS_URL")

    webhook_base_url: Optional[str] = os.getenv("WEBHOOK_BASE_URL")
    admin_bot_webhook_base_url: Optional[str] = os.getenv("ADMIN_BOT_WEBHOOK_BASE_URL")
    webhook_host: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    webhook_port: int = _get_int_with_default(os.getenv("WEBHOOK_PORT"), 8080)
    admin_telegram_ids: Tuple[int, ...] = tuple(_get_int_list(os.getenv("ADMIN_TELEGRAM_IDS")))

    main_gallery_channel_id: Optional[int] = _get_int(os.getenv("MAIN_GALLERY_CHANNEL_ID"))
    model_dashboard_channel_id: Optional[int] = _get_int(os.getenv("MODEL_DASHBOARD_CHANNEL_ID"))
    escrow_log_channel_id: Optional[int] = _get_int(os.getenv("ESCROW_LOG_CHANNEL_ID"))

    paystack_secret_key: Optional[str] = os.getenv("PAYSTACK_SECRET_KEY")
    flutterwave_secret_key: Optional[str] = os.getenv("FLUTTERWAVE_SECRET_KEY")

    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN")

    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    supabase_bucket: str = os.getenv("SUPABASE_BUCKET", "media")

    secret_key: Optional[str] = os.getenv("SECRET_KEY")
    encryption_key: Optional[str] = os.getenv("ENCRYPTION_KEY")


settings = Settings()
