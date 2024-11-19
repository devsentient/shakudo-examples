cd backend-dify-opensource/

apt-get update -y && apt-get upgrade -y
apt-get install -y dnsutils postgresql
pip install -r requirements.txt
uvicorn app_dify:app --workers 1 --port 8000
