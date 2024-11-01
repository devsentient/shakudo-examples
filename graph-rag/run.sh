cd graph-rag

apt-get update -y && apt-get upgrade -y

pip install -r requirements.txt
uvicorn app:app --workers 1 --port 8000 --host 0.0.0.0