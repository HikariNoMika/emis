"""Background execution of large import batches."""

from app.celery_app import celery


@celery.task(name="emis.process_import", bind=True)
def process_import_task(self, batch_id, user_id):
    """Run the import in the Celery worker.

    Imports are local so importing this module never pulls the whole Flask app
    into the worker process at startup.
    """
    from app.extensions import db
    from app.models import ImportBatch
    from app.processors.import_processor import execute_import
    from app.services.audit_service import log_action
    from app.utils.time import utcnow

    batch = db.session.get(ImportBatch, batch_id)
    if batch is None:
        raise ValueError(f"Import batch {batch_id} does not exist.")

    try:
        summary = execute_import(batch, user_id)
        log_action(
            "IMPORT_PROCESSED",
            "imports",
            record_identifier=batch_id,
            new_values=summary,
            user_id=user_id,
        )
        return summary
    except Exception as exc:
        # Mark the batch as failed so the UI does not show it as stuck.
        batch.status = "FAILED"
        batch.notes = f"Background import failed: {exc}"
        batch.completed_at = utcnow()
        db.session.commit()
        raise
