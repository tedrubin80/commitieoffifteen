FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /workspace/src/
COPY README.md /workspace/README.md

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace \
    DATA_DIR=/workspace/data

EXPOSE 8891 8504

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8891", "--no-browser", "--allow-root", \
     "--NotebookApp.token=", "--NotebookApp.password="]
