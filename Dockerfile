FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ghostscript \
    poppler-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uv && uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY server/requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt
COPY server/ .
CMD ["sh", "-c", "gunicorn --worker-class gevent --bind 0.0.0.0:$PORT --timeout 120 app:app"]
