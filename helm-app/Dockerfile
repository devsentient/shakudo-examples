FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app.py app.py

EXPOSE 80

CMD ["fastapi", "run", "app.py", "--port", "80"]
