FROM  python:3.10.13-bullseye as backend_img


RUN mkdir /app
WORKDIR /app
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y dnsutils postgresql
COPY *.txt ./app/
RUN pip install -r ./app/requirements.txt
COPY *.py ./app/
WORKDIR /app