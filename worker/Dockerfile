FROM python:3.12-slim

WORKDIR /app

COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ /app/worker/
COPY db/ /app/db/

WORKDIR /app/worker

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
