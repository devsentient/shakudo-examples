#!/bin/bash

cd pdf-ingestion
pip install -r requirements.txt
mkdir -p cleanned_md
mkdir -p pdf_output
python download_pdf_files.py
python cleanup.py
python neo4j_ingest.py