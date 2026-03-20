FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY gunicorn_conf.py .

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn_conf.py", "app.main:app", "-k", "uvicorn.workers.UvicornWorker"]

