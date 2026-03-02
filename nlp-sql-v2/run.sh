#!/bin/bash
# Working directory is already /tmp/git/monorepo/nlp-sql-v2/

apt-get update -y && apt-get upgrade -y
apt-get install -y dnsutils postgresql

pip install -r requirements.txt

# Start the Vanna AI microservice
uvicorn app:app --workers 1 --port 8787 --host 0.0.0.0
