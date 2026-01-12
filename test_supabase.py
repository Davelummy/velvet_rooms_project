from supabase_storage import upload_file, get_public_url

local_file = "test_image.png"
bucket = None
remote_file = "test/test_image.png"

# Upload
result = upload_file(local_file, bucket, remote_file)
print("Upload result:", result)

# Get public URL
url = get_public_url(bucket, remote_file)
print("Public URL:", url)
