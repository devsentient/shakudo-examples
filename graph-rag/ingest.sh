cd graph-rag

apt-get update -y && apt-get upgrade -y

pip install -r requirements.txt
python -m pip install -U pypdfium2

DATA_DIR="graphrag-data"

python ocr_preprocess.py DATADIR
python ingest.py DATADIR
