FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telemetry_logger.py .
COPY query_recent.py .
COPY export_csv.py .

CMD ["python", "telemetry_logger.py"]
