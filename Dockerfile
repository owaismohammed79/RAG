FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ghostscript \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ .
