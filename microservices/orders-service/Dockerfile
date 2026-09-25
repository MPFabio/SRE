FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install --yes --no-install-recommends curl \
    && rm --recursive --force /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash --uid 10001 appuser

COPY requirements-base.txt .
COPY orders-service/requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY _shared/ ./_shared/
COPY orders-service/main.py .

EXPOSE 8083

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl --fail --silent --show-error http://localhost:8083/health || exit 1

USER appuser

CMD ["python", "main.py"]
