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

def check_files_in_bucket(minio_client, bucket_name, file_list):
    non_existing_files = []
    
    for file_name in file_list:
        file_name = file_name.strip()  # Remove any leading/trailing whitespace
        if file_name:  # Check if the filename is not empty
            exists = file_exists_in_bucket(minio_client, bucket_name, file_name)
            if not exists:
                non_existing_files.append(file_name)
    
    return non_existing_files

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <filename>")
        sys.exit(1)

    input_file = sys.argv[1]

    minio_url = "minio.hyperplane-minio.svc.cluster.local:9000"
    access_key = "5fDcdMMayNJkFWZlL9aD"
    secret_key = "XzImiZeh0uBGEUACH8RPAoFqrxNnHISF9x8XqoQ4"
    minio_client = Minio(minio_url, access_key=access_key, secret_key=secret_key, secure=False)
    bucket_name = "batch-job-test"

    try:
        with open(input_file, 'r') as f:
            file_list = f.readlines()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    non_existing_files = check_files_in_bucket(minio_client, bucket_name, file_list)

    # Print non-existing files if any
    if non_existing_files:
        print("\nThe following files do not exist in the bucket:")
        for file in non_existing_files:
            print(file)
    else:
        print("\nAll files exist in the bucket.")
