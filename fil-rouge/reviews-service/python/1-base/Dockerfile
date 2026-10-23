FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY main.py .

USER 10001
EXPOSE 8086

CMD ["python", "main.py"]
