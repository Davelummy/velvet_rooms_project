import argparse
from supabase_storage import upload_file
from config import settings


def main():
    parser = argparse.ArgumentParser(description="Upload a backup file to Supabase Storage")
    parser.add_argument("file", help="Path to backup file")
    parser.add_argument("--remote", default=None, help="Remote storage path")
    args = parser.parse_args()

    remote_path = args.remote or f"backups/{args.file.rsplit('/', 1)[-1]}"
    upload_file(args.file, settings.supabase_bucket, remote_path)
    print(f"✅ Uploaded to supabase://{settings.supabase_bucket}/{remote_path}")


if __name__ == "__main__":
    main()
