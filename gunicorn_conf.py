import os

bind_host = os.getenv("APP_HOST", "0.0.0.0")
bind_port = os.getenv("PORT", os.getenv("APP_PORT", "8000"))
bind = f"{bind_host}:{bind_port}"
workers = int(os.getenv("APP_WORKERS", "2"))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
