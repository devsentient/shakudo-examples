import os
from minio import Minio
from minio.error import S3Error

# Get MinIO server details from environment variables
minio_host = os.getenv("MINIO_HOST", "minio.hyperplane-minio:9000")
access_key = os.getenv("HYPERPLANE_CUSTOM_SECRET_KEY_MINIO_ACCESS_KEY")
secret_key = os.getenv("HYPERPLANE_CUSTOM_SECRET_KEY_MINIO_SECRET_KEY")

if not access_key or not secret_key:
    raise Exception("MINIO_ACCESS_KEY or MINIO_SECRET_KEY is empty.")

# Create a Minio client instance
minio_client = Minio(
    minio_host,
    access_key=access_key,
    secret_key=secret_key,
    secure=False
)

def download_all_files(bucket_name, prefix, download_dir):
    try:
        # Check if the bucket exists
        if not minio_client.bucket_exists(bucket_name):
            print(f"Bucket {bucket_name} does not exist!")
            return

        # List all objects under the given prefix (recursively)
        objects = minio_client.list_objects(bucket_name, prefix=prefix, recursive=True)
        
        for obj in objects:
            # Build local file path, preserving sub-directory structure
            relative_path = obj.object_name[len(prefix):].lstrip("/")
            local_file_path = os.path.join(download_dir, relative_path)
            
            # Ensure the target directory exists
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            # Download the file
            minio_client.fget_object(bucket_name, obj.object_name, local_file_path)
            print(f"Downloaded {obj.object_name} to {local_file_path}")
    
    except S3Error as e:
        print(f"An error occurred: {e}")

# Usage
bucket_name = os.getenv('BUCKET_NAME', 'shakudo-poc')
object_prefix = os.getenv('OBJECT_KEY', 'rag-chat-financial10k/pdfs/')
download_path = './pdf_input'

if not bucket_name or not object_prefix or not download_path:
    print("Please set all the required environment variables.")
else:
    download_all_files(bucket_name, object_prefix, download_path)
