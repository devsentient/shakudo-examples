####
# python search_minio.py <FILENAME>
####


from minio import Minio
from minio.error import S3Error
import sys

def file_exists_in_bucket(minio_client, bucket_name, file_name):
    try:
        minio_client.stat_object(bucket_name, file_name)
        print(f"File '{file_name}' exists in bucket '{bucket_name}'.")
        return True
    except S3Error as e:
        if e.code == 'NoSuchKey':
            print(f"File '{file_name}' does not exist in bucket '{bucket_name}'.")
            return False
        else:
            print(f"An error occurred: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <filename>")
        sys.exit(1)

    file_name = sys.argv[1]

    minio_url = "minio.hyperplane-minio.svc.cluster.local:9000"
    access_key = "5fDcdMMayNJkFWZlL9aD"
    secret_key = "XzImiZeh0uBGEUACH8RPAoFqrxNnHISF9x8XqoQ4"
    minio_client = Minio(minio_url, access_key=access_key, secret_key=secret_key, secure=False)
    bucket_name = "batch-job-test"

    file_exists_in_bucket(minio_client, bucket_name, file_name)