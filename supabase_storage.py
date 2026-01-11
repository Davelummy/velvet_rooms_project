import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_KEY missing from .env")

if not SUPABASE_URL.endswith("/"):
    SUPABASE_URL += "/"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def upload_file(local_path: str, bucket: str, remote_path: str):
    """Upload a file to Supabase Storage, overwriting if it already exists."""
    # Delete first if exists
    try:
        supabase.storage.from_(bucket).remove([remote_path])
    except Exception:
        pass  # ignore if it doesn't exist

    with open(local_path, "rb") as f:
        res = supabase.storage.from_(bucket).upload(remote_path, f)
    return res

def get_public_url(bucket: str, remote_path: str) -> str:
    """Return the public URL of a file in Supabase storage."""
    return supabase.storage.from_(bucket).get_public_url(remote_path)

