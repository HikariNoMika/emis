"""Thread-safe, process-local progress for inline import processing.

A single uvicorn process serves the progress endpoint while the synchronous
import runs in a worker thread, so the browser can poll during a long import.
Celery workers use a separate process; there the endpoint falls back to the
stored batch status (see routes/imports.py).
"""

import threading
from datetime import datetime, timezone

_lock = threading.Lock()
_jobs = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def start(batch_id, total_rows=0, message="Starting import…"):
    job = {
        "batch_id": int(batch_id),
        "status": "RUNNING",
        "total_rows": int(total_rows or 0),
        "processed_rows": 0,
        "percent": 0,
        "message": message,
        "started_at": _now(),
        "finished_at": None,
        "result": None,
        "error": None,
    }
    with _lock:
        _jobs[int(batch_id)] = job
    return job


def update(batch_id, processed_rows=None, total_rows=None, message=None):
    with _lock:
        job = _jobs.get(int(batch_id))
        if job is None:
            return
        if processed_rows is not None:
            job["processed_rows"] = int(processed_rows)
        if total_rows is not None:
            job["total_rows"] = int(total_rows)
        total = job["total_rows"]
        job["percent"] = (
            min(100, round(job["processed_rows"] * 100 / total)) if total else 0
        )
        if message:
            job["message"] = message


def finish(batch_id, result=None, error=None):
    with _lock:
        job = _jobs.get(int(batch_id))
        if job is None:
            return
        job["status"] = "FAILED" if error else "COMPLETED"
        if result:
            job["result"] = result
            job["processed_rows"] = result.get("total_rows", job["processed_rows"])
            job["percent"] = 100
        job["error"] = error
        job["message"] = f"Failed: {error}" if error else "Import complete."
        job["finished_at"] = _now()


def get(batch_id):
    with _lock:
        job = _jobs.get(int(batch_id))
        return dict(job) if job else None
