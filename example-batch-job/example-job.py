from minio import Minio
import time, os
from io import BytesIO

time.sleep(10)

MINIO_ENDPOINT = "minio.hyperplane-minio.svc.cluster.local:9000"
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

bucket_name = "batch-job-test"
file_id = os.getenv('FILE_ID')
object_name = f"{file_id}.txt" 
file_content = f"Hello, MinIO! This is a test string in {object_name}."  
file_data = BytesIO(file_content.encode('utf-8'))

try:
    minio_client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=file_data,
        length=len(file_content), 
        content_type="text/plain"
    )
    print(f"Text file '{object_name}' successfully uploaded to bucket '{bucket_name}'.")
except S3Error as e:
    raise Exception(f"Failed to upload file: {str(e)}")