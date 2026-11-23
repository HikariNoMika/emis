"""Accomplishment report generation, finalization and revision endpoints."""

import os

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.schemas import ReportGenerate, ReportRevise
from app.services import (
    accomplishment_reporting_service as reporting,
    accomplishment_service as service,
)
from app.utils.responses import ok
from app.utils.security import get_current_user
from app.utils.serializers import accomplishment_report_to_dict

accomplishment_reports_bp = APIRouter()


def _require_admin(user=Depends(get_current_user)):
    from app.services.exceptions import ValidationAppError

    if getattr(user, "role", "admin") != "admin":
        raise ValidationAppError("Only administrators may finalize or revise reports.")
    return user


@accomplishment_reports_bp.post("/reports/generate", status_code=201)
def generate_report(payload: ReportGenerate, user=Depends(get_current_user)):
    return ok(data=accomplishment_report_to_dict(
        service.generate_report(payload.model_dump(), user.id)
    ), message="Accomplishment report created as DRAFT.")


@accomplishment_reports_bp.get("/reports")
def list_reports(user=Depends(get_current_user)):
    return ok(data=service.reports())


@accomplishment_reports_bp.get("/reports/{report_id}")
def get_report(report_id: int, user=Depends(get_current_user)):
    return ok(data=service.report_detail(report_id))


@accomplishment_reports_bp.post("/reports/{report_id}/file")
def build_file(report_id: int, file_format: str = "pdf", user=Depends(get_current_user)):
    report = service.get_report(report_id)
    path, name = reporting.generate_file(report, file_format)
    from app.extensions import db
    db.session.commit()
    return ok(data={"file_name": name, "file_path": path}, message="Report file generated.")


@accomplishment_reports_bp.get("/reports/{report_id}/download")
def download(report_id: int, user=Depends(get_current_user)):
    report = service.get_report(report_id)
    if not report.file_path or not os.path.exists(report.file_path):
        from app.services.exceptions import NotFoundError
        raise NotFoundError("Report file has not been generated yet.")
    with open(report.file_path, "rb") as handle:
        content = handle.read()
    media_type = (
        "application/pdf" if report.file_format == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{report.file_name}"'},
    )


@accomplishment_reports_bp.post("/reports/{report_id}/finalize")
def finalize(report_id: int, user=Depends(_require_admin)):
    return ok(data=accomplishment_report_to_dict(
        service.finalize_report(report_id, user.id)
    ), message="Report finalized and snapshot frozen.")


@accomplishment_reports_bp.post("/reports/{report_id}/revise", status_code=201)
def revise(report_id: int, payload: ReportRevise, user=Depends(_require_admin)):
    return ok(data=accomplishment_report_to_dict(
        service.revise_report(report_id, payload.model_dump(), user.id)
    ), message="Authorized revision created.")
