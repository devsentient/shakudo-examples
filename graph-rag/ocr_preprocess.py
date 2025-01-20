from minio import Minio
from minio.error import S3Error
import os, glob, sys
import pypdfium2 as pdfium

# Access Dataset
DATASET_MINIO_ENDPOINT = os.environ.get("DATASET_MINIO_ENDPOINT", 'minio.hyperplane-minio.svc.cluster.local:9000')
DATASET_MINIO_ACCESS_KEY = os.environ.get('DATASET_MINIO_ACCESS_KEY', "")
DATASET_MINIO_ACCESS_KEY_SECRET = os.environ.get('DATASET_MINIO_ACCESS_KEY_SECRET', "")

class MinioDownloader:
    def __init__(self, endpoint, access_key, secret_key):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
    def download_bucket(self, bucket_name, prefix, local_folder):
        try:
            os.makedirs(local_folder, exist_ok=True)
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            for obj in objects:
                local_file_path = os.path.join(local_folder, os.path.basename(obj.object_name))
                self.client.fget_object(bucket_name, obj.object_name, local_file_path)
            print("Download complete.")
        except S3Error as e:
            print(f"Error downloading files: {e}")

# OCR
def ocr_get_text(src, dst):
  os.makedirs(dst, exist_ok=True)
  pdf_files = glob.glob(os.path.join(src, "**/*.pdf"), recursive=True)
  res = []
  for pdf_file in pdf_files:
    pdf = pdfium.PdfDocument(pdf_file)
    all_texts = "\n ".join([f"Page {[i+1]}: \n" + pdf[i].get_textpage().get_text_range() for i in range(len(pdf))])

    txt_filename = pdf_file.split("/")[-1].split(".")[0] + '.txt'
    with open(os.path.join(dst, txt_filename), "w", encoding="utf-8") as f:
      f.write(all_texts)
    
    print(f"{pdf_file} preprocessed. Output: {txt_filename}")

if __name__ == "__main__":
    DATADIR = None
    if len(sys.argv) > 1:
      DATADIR = sys.argv[1]
      print(f"DATADIR: {DATADIR}")
    else:
      print("No arguments were provided.")
      exit()

    DATADIR_PDF = f'./{DATADIR}/raw'
    DATADIR_TXT = f'./{DATADIR}/txt'
    downloader = MinioDownloader(DATASET_MINIO_ENDPOINT, DATASET_MINIO_ACCESS_KEY, DATASET_MINIO_ACCESS_KEY_SECRET)
    downloader.download_bucket("datasets", "10ks", DATADIR_PDF)

    ocr_get_text(DATADIR_PDF, DATADIR_TXT)

    print("OCR STEP COMPLETED.")
