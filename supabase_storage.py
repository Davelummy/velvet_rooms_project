from typing import Optional

from supabase import create_client, Client
from config import settings

if not settings.supabase_url or not settings.supabase_service_key:
    raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_KEY missing from .env")

supabase_url = settings.supabase_url
if not supabase_url.endswith("/"):
    supabase_url += "/"

supabase: Client = create_client(supabase_url, settings.supabase_service_key)

def upload_file(local_path: str, bucket: Optional[str], remote_path: str):
    """Upload a file to Supabase Storage, overwriting if it already exists."""
    bucket = bucket or settings.supabase_bucket
    # Delete first if exists
    try:
        supabase.storage.from_(bucket).remove([remote_path])
    except Exception:
        pass  # ignore if it doesn't exist

    with open(local_path, "rb") as f:
        res = supabase.storage.from_(bucket).upload(remote_path, f)
    return res

def get_public_url(bucket: Optional[str], remote_path: str) -> str:
    """Return the public URL of a file in Supabase storage."""
    bucket = bucket or settings.supabase_bucket
    return supabase.storage.from_(bucket).get_public_url(remote_path)
