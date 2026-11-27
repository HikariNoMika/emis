"""Report endpoints."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.schemas import ReportGenerateSchema
from app.services import report_service
from app.utils.responses import ok, paginated
from app.utils.security import get_current_user
from app.utils.serializers import report_to_dict

reports_bp = APIRouter()


@reports_bp.get("")
def list_reports(
    page: int = Query(1, ge=1), per_page: int = Query(25, ge=1, le=100),
    user=Depends(get_current_user),
):
    pagination = report_service.list_reports(page, per_page)
    return paginated(
        [report_to_dict(r) for r in pagination.items],
        page, per_page, pagination.total,
    )


@reports_bp.post("/generate", status_code=201)
def generate_report(payload: ReportGenerateSchema, user=Depends(get_current_user)):
    data = payload.model_dump()
    report = report_service.generate(data, user.id, job_id=data.get("job_id"))
    return ok(data=report_to_dict(report), message="Report generated.")


@reports_bp.get("/progress/{job_id}")
def report_progress(job_id: str, user=Depends(get_current_user)):
    """Live progress for a running report generation."""
    from app.utils import report_progress as progress
    status = progress.get(job_id)
    if status is None:
        from app.services.exceptions import NotFoundError
        raise NotFoundError("Report job not found.")
    return ok(data=status)


@reports_bp.get("/{report_id}")
def get_report(report_id: int, user=Depends(get_current_user)):
    return ok(data=report_to_dict(report_service.get_report(report_id)))


@reports_bp.get("/{report_id}/download")
def download_report(report_id: int, user=Depends(get_current_user)):
    report = report_service.get_report(report_id)
    try:
        with open(report.file_path, "rb") as handle:
            content = handle.read()
    except OSError:
        from app.services.exceptions import NotFoundError
        raise NotFoundError("Report file is missing.")

    media_types = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_types.get(
        report.file_format, "application/octet-stream"
    )
    return Response(
        content, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{report.file_name}"'},
    )
