# supabase_storage.py
import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "media")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def upload_file(file_path: str, storage_path: str):
    """
    Uploads a local file to Supabase storage.
    :param file_path: Local file path
    :param storage_path: Path in Supabase bucket (e.g., 'models/123/photo.jpg')
    """
    with open(file_path, "rb") as f:
        response = supabase.storage.from_(SUPABASE_BUCKET).upload(storage_path, f)
    return response

async def get_public_url(storage_path: str):
    """
    Get public URL of a file.
    """
    url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
    return url

