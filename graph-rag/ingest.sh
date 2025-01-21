cd graph-rag

apt-get update -y && apt-get upgrade -y

pip install -r requirements.txt
pip install -U pypdfium2 minio
export DATADIR=graphrag-data

python ocr_preprocess.py $DATADIR
python ingest.py $DATADIR
