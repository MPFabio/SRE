FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash --uid 10001 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY locustfile.py .

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8089

ENV LOCUST_USERS=10
ENV LOCUST_SPAWN_RATE=1
ENV LOCUST_RUN_TIME=0
ENV LOCUST_HOST=http://api-gateway:8080

USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]