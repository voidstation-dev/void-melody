"""Runtime pack management API."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, status

from app.config import settings
from app.services.plan_enforcement import check_request_feature
from app.services.runtime_manager import RuntimeManagerService
from app.services.runtime_manager.models import RuntimeManagerError
from app.services.runtime_manager.manifests import KNOWN_RUNTIME_IDS

router = APIRouter()
logger = logging.getLogger(__name__)

_service = RuntimeManagerService()


def _to_http(code: str) -> int:
    if code == "UNKNOWN_RUNTIME":
        return status.HTTP_404_NOT_FOUND
    if code in ("NO_DOWNLOAD_URL", "CANNOT_REMOVE_ACTIVE"):
        return status.HTTP_400_BAD_REQUEST
    if code.startswith("DOWNLOAD_") or code in ("CHECKSUM_MISMATCH", "UNSAFE_ZIP_ENTRY"):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    return status.HTTP_500_INTERNAL_SERVER_ERROR


@router.get("/runtimes")
async def list_runtimes():
    return {"items": [s.to_dict() for s in _service.list_statuses()]}


@router.get("/runtimes/{runtime_id}/status")
async def runtime_status(runtime_id: str):
    try:
        return _service.status(runtime_id).to_dict()
    except RuntimeManagerError as exc:
        raise HTTPException(status_code=_to_http(exc.code), detail={"code": exc.code, "message": exc.message})


@router.post("/runtimes/{runtime_id}/install")
async def install_runtime(
    runtime_id: str,
    file: UploadFile = File(...),  # noqa: B008
    request: Request = None,  # noqa: B008
):
    """Install a runtime pack from an uploaded ZIP.

    Requires the runtime_install plan feature.
    """
    check_request_feature(request, "runtime_install")
    try:
        tmp_dir = settings.custom_voices_dir / ".runtime-uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_zip = tmp_dir / file.filename
        with open(tmp_zip, "wb") as f:
            while chunk := await file.read(65536):
                f.write(chunk)
        result = _service.install(runtime_id, zip_path=tmp_zip)
        tmp_zip.unlink(missing_ok=True)
        return result.to_dict()
    except RuntimeManagerError as exc:
        raise HTTPException(status_code=_to_http(exc.code), detail={"code": exc.code, "message": exc.message})
    except Exception as exc:
        logger.exception("runtime install failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/runtimes/{runtime_id}/update")
async def update_runtime(runtime_id: str, file: UploadFile = File(...)):  # noqa: B008
    try:
        tmp_dir = settings.custom_voices_dir / ".runtime-uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_zip = tmp_dir / file.filename
        with open(tmp_zip, "wb") as f:
            while chunk := await file.read(65536):
                f.write(chunk)
        result = _service.update(runtime_id, zip_path=tmp_zip)
        tmp_zip.unlink(missing_ok=True)
        return result.to_dict()
    except RuntimeManagerError as exc:
        raise HTTPException(status_code=_to_http(exc.code), detail={"code": exc.code, "message": exc.message})
    except Exception as exc:
        logger.exception("runtime update failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/runtimes/{runtime_id}/repair")
async def repair_runtime(runtime_id: str):
    try:
        return _service.repair(runtime_id).to_dict()
    except RuntimeManagerError as exc:
        raise HTTPException(status_code=_to_http(exc.code), detail={"code": exc.code, "message": exc.message})


@router.delete("/runtimes/{runtime_id}")
async def remove_runtime(runtime_id: str):
    try:
        _service.remove(runtime_id)
        return {"id": runtime_id, "removed": True}
    except RuntimeManagerError as exc:
        raise HTTPException(status_code=_to_http(exc.code), detail={"code": exc.code, "message": exc.message})


@router.post("/runtimes/{runtime_id}/rollback")
async def rollback_runtime(runtime_id: str):
    try:
        return _service.rollback(runtime_id).to_dict()
    except RuntimeManagerError as exc:
        raise HTTPException(status_code=_to_http(exc.code), detail={"code": exc.code, "message": exc.message})