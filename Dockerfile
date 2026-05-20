FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ocrmypdf \
    ghostscript \
    poppler-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
RUN pip install uv && uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV CHROMA_PATH=/app/chroma
COPY server/requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt
COPY server/ .
RUN mkdir -p $CHROMA_PATH
CMD ["sh", "-c", "gunicorn --worker-class gthread --workers 1 --threads 4 --bind 0.0.0.0:$PORT --timeout 120 app:app"]