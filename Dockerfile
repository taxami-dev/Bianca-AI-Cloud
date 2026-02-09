FROM runpod/pytorch:2.1-py3.11-cuda11.8.0-devel-ubuntu22.04

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs data/cache agents/models

ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y curl wget git && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["python", "main.py"]
