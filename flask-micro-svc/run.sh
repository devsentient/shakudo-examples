#!/bin/bash

cd flask-micro-svc/

pip install -r requirements.txt

# -w indicates the number of workers that will receive your incoming request. Can increase this number for better throughput
gunicorn -w 1 -b 0.0.0.0:8000 app:app