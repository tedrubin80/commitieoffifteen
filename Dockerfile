FROM python:3.12-slim

WORKDIR /app

COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ /app/worker/
COPY db/ /app/db/

WORKDIR /app/worker

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn railway_app:app --host 0.0.0.0 --port ${PORT:-8080}"]
