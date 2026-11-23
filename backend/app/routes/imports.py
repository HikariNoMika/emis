"""Data import endpoints."""

import shutil

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.schemas import ImportMappingSchema, ImportQuerySchema
from app.services import import_service
from app.services.exceptions import NotFoundError, ValidationAppError
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.serializers import import_batch_to_dict

imports_bp = APIRouter()


class UploadAdapter:
    """Adapts FastAPI's UploadFile to the simple interface the service expects."""

    def __init__(self, upload: UploadFile):
        self.filename = upload.filename
        self._file = upload.file

    def save(self, path):
        self._file.seek(0)
        with open(path, "wb") as target:
            shutil.copyfileobj(self._file, target)


def _get_batch(batch_id):
    batch = import_service.get_batch(batch_id)
    if batch is None:
        raise NotFoundError("Import batch not found.")
    return batch


@imports_bp.post("/upload", status_code=201)
async def upload(
    file: UploadFile = File(...),
    station_id: int | None = Form(None),
    sheet_name: str | None = Form(None),
    user=Depends(get_current_user),
):
    batch = import_service.upload(UploadAdapter(file), user.id, station_id, sheet_name)
    return ok(
        data=import_batch_to_dict(batch),
        message="File uploaded and inspected. Review the mapping before processing.",
    )


@imports_bp.get("")
def list_imports(filters: ImportQuerySchema = Depends(), user=Depends(get_current_user)):
    data = filters.model_dump()
    pagination = import_service.list_batches(data, data["page"], data["per_page"])
    return paginated(
        [import_batch_to_dict(b) for b in pagination.items],
        pagination.page, pagination.per_page, pagination.total,
    )


@imports_bp.get("/{batch_id}")
def get_import(batch_id: int, user=Depends(get_current_user)):
    return ok(data=import_batch_to_dict(_get_batch(batch_id)))


@imports_bp.get("/{batch_id}/preview")
def preview_import(
    batch_id: int, limit: int = Query(50, ge=1, le=200), user=Depends(get_current_user)
):
    return ok(data=import_service.preview(_get_batch(batch_id), limit))


@imports_bp.put("/{batch_id}/mapping")
def update_mapping(
    batch_id: int, payload: ImportMappingSchema, user=Depends(get_current_user)
):
    data = payload.model_dump(exclude_unset=True)
    data = {key: value for key, value in data.items() if value is not None}
    batch = import_service.update_mapping(_get_batch(batch_id), data, user.id)
    return ok(data={"column_mapping": batch.column_mapping}, message="Mapping saved.")


@imports_bp.post("/{batch_id}/process")
def process_import(batch_id: int, user=Depends(get_current_user)):
    result = import_service.process_batch(_get_batch(batch_id), user.id)
    from app.utils.responses import success
    return success(
        data=result,
        message="Import processed.",
        status_code=202 if result.get("queued") else 200,
    )


@imports_bp.get("/{batch_id}/errors")
def import_errors(batch_id: int, user=Depends(get_current_user)):
    return ok(data=import_service.get_errors(_get_batch(batch_id)))
