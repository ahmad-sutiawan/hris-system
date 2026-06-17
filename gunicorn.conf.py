import multiprocessing
import os


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name, "").strip()
    return raw or default


bind = _env_str("GUNICORN_BIND", "0.0.0.0:8000")
workers = _env_int("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1)
threads = _env_int("GUNICORN_THREADS", 4)
worker_class = _env_str("GUNICORN_WORKER_CLASS", "gthread")
timeout = _env_int("GUNICORN_TIMEOUT", 120)
preload_app = _env_str("GUNICORN_PRELOAD", "true").lower() in ("1", "true", "yes")
max_requests = _env_int("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _env_int("GUNICORN_MAX_REQUESTS_JITTER", 100)
accesslog = "-"
errorlog = "-"
loglevel = _env_str("GUNICORN_LOG_LEVEL", "info")
