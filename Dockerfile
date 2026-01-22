FROM python:3.11-slim

WORKDIR /app

# Systemabhängigkeiten für pdfplumber installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

# Cache-Verzeichnis erstellen
RUN mkdir -p /app/cache

EXPOSE 5123

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5123/api/health || exit 1

CMD ["python", "api_server.py"]
