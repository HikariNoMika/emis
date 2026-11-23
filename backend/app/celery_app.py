"""Celery application for background EMIS jobs."""

import os

from celery import Celery, Task
from celery.signals import worker_process_init


class DBTask(Task):
    """Releases the SQLAlchemy scoped session after every task."""

    def __call__(self, *args, **kwargs):
        from app.extensions import db

        try:
            return self.run(*args, **kwargs)
        finally:
            db.remove()


celery = Celery(
    "emis",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    task_cls=DBTask,
)

celery.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)


@worker_process_init.connect
def _init_database(**_kwargs):
    """Each worker process needs its own engine/session factory."""
    from app.config import get_settings
    from app.extensions import db

    db.init(get_settings(os.getenv("APP_ENV", "development")))


@celery.task(name="emis.ping")
def ping():
    return "pong"


# Import task modules so the worker registers their names at startup.
# Without this, queued tasks are received but discarded with
# "KeyError: 'emis.process_import'".
from app.tasks import import_tasks  # noqa: E402,F401
