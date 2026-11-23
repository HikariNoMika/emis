FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System packages needed by psycopg2 and OpenPyXL/Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", "run:app"]
