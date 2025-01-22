cd pdf_server/

# apt-get install -y dnsutils postgresql
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8787
