from minio import Minio
from minio.error import S3Error
import os

class MinioDownloader:
    def __init__(self, endpoint, access_key, secret_key):
        """
        Initialize the MinIO client.

        :param endpoint: MinIO server endpoint (e.g., "play.min.io:9000").
        :param access_key: Access key for MinIO.
        :param secret_key: Secret key for MinIO.
        """
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )

    def download_bucket(self, bucket_name, prefix, local_folder):
        """
        Download all files from a bucket/prefix to a local folder.

        :param bucket_name: Name of the MinIO bucket.
        :param prefix: Prefix in the bucket (e.g., "datasets/10ks").
        :param local_folder: Local folder where files will be downloaded.
        """
        try:
            # Ensure the local folder exists
            os.makedirs(local_folder, exist_ok=True)

            # List objects in the bucket with the specified prefix
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)

            for obj in objects:
                local_file_path = os.path.join(local_folder, os.path.basename(obj.object_name))
                print(f"Downloading {obj.object_name} to {local_file_path}...")

                # Download the object
                self.client.fget_object(bucket_name, obj.object_name, local_file_path)

            print("Download complete.")

        except S3Error as e:
            print(f"Error downloading files: {e}")

