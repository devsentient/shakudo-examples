#!/bin/bash

cd pdf-ingestion
pip install -r requirements.txt
uvicorn neo4j_app:app --reload --port 8787 --host 0.0.0.0