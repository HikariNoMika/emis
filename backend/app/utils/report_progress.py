"""Thread-safe, process-local progress for synchronous report generation.

The browser starts a report, then polls this endpoint while the request runs
in a FastAPI worker thread. Keyed by a client-supplied job id so several
reports can be generated without colliding.
"""

import threading
from datetime import datetime, timezone

_lock = threading.Lock()
_jobs = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def start(job_id, total_steps=0, message="Preparing report…"):
    job = {
        "job_id": str(job_id),
        "status": "RUNNING",
        "step": 0,
        "total_steps": int(total_steps or 0),
        "percent": 0,
        "message": message,
        "started_at": _now(),
        "finished_at": None,
        "error": None,
    }
    with _lock:
        _jobs[str(job_id)] = job
    return job


def update(job_id, step=None, message=None):
    with _lock:
        job = _jobs.get(str(job_id))
        if job is None:
            return
        if step is not None:
            job["step"] = int(step)
        total = job["total_steps"]
        job["percent"] = min(100, round(job["step"] * 100 / total)) if total else 0
        if message:
            job["message"] = message


def finish(job_id, error=None, message="Report ready."):
    with _lock:
        job = _jobs.get(str(job_id))
        if job is None:
            return
        job["status"] = "FAILED" if error else "COMPLETED"
        job["percent"] = 100 if not error else job["percent"]
        job["error"] = error
        job["message"] = f"Failed: {error}" if error else message
        job["finished_at"] = _now()


def get(job_id):
    with _lock:
        job = _jobs.get(str(job_id))
        return dict(job) if job else None
