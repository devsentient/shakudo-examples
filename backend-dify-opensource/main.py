from minio_download import MinioDownloader

def main():
    # Replace with your MinIO credentials and configuration
    endpoint = "minio.hyperplane-minio.svc.cluster.local:9000"  # e.g., "play.min.io:9000"
    access_key = "Lnwp6tuWSDm6pxOSC8Y9"
    secret_key = "OE22R4agACojDY8fiVJQa3ZyQ9ivkhcfBiKh3WgI"
    bucket_name = "datasets"
    prefix = "10ks"
    local_folder = "datasets/10ks"

    # Initialize the MinioDownloader
    downloader = MinioDownloader(endpoint, access_key, secret_key)

    # Download files from the bucket
    downloader.download_bucket(bucket_name, prefix, local_folder)

if __name__ == "__main__":
    main()
