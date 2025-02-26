FROM gcr.io/devsentient-infra/dev/jhub-basic:v1.0.0

WORKDIR /app

RUN pwd
COPY . /build-context
RUN ls -la /build-context

COPY example-image-nested/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt