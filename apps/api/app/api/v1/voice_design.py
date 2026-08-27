"""Voice Design API for OmniVoice / G-OmniVoice.

Describe → Preview → Save flow, isolated from VieNeu Voice Lab cloning.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.schemas.voice_design import (
    VoiceDesignCapabilitiesResponse,
    VoiceDesignCommitRequest,
    VoiceDesignCommitResponse,
    VoiceDesignPreviewRequest,
    VoiceDesignPreviewResponse,
    VoiceDesignSessionResponse,
)
from app.services.plan_enforcement import check_request_feature
from app.services.voice_design import VoiceDesignOrchestrator
from app.services.voice_design.preview_store import (
    get_candidate_audio_path,
    load_session,
)
from app.services.omnivoice_model_service import omnivoice_model_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_orchestrator() -> VoiceDesignOrchestrator:
    return VoiceDesignOrchestrator()


@router.get(
    "/tts/voice-design/capabilities",
    response_model=VoiceDesignCapabilitiesResponse,
)
async def voice_design_capabilities() -> VoiceDesignCapabilitiesResponse:
    """Return whether Voice Design (OmniVoice) is available on this installation."""
    installed = omnivoice_model_service.is_installed()
    if not installed:
        return VoiceDesignCapabilitiesResponse(
            enabled=False,
            providerId="omnivoice",
            engineId="g-omnivoice",
            modelInstalled=False,
            supportsPromptDesign=True,
            supportsVoiceClone=False,
            reasonCode="OMNI_MODEL_NOT_INSTALLED",
            reason="G-OmniVoice model is not installed.",
        )
    return VoiceDesignCapabilitiesResponse(
        enabled=True,
        providerId="omnivoice",
        engineId="g-omnivoice",
        modelInstalled=True,
        supportsPromptDesign=True,
        supportsVoiceClone=False,
    )


@router.post(
    "/tts/voice-design/previews",
    status_code=status.HTTP_201_CREATED,
    response_model=VoiceDesignPreviewResponse,
)
async def create_voice_design_previews(
    req: VoiceDesignPreviewRequest,
    request: Request = None,  # noqa: B008
    orchestrator: VoiceDesignOrchestrator = Depends(_get_orchestrator),  # noqa: B008
):
    """Generate candidate preview voices from a description."""
    check_request_feature(request, "voice_design")
    caps = await voice_design_capabilities()
    if not caps.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": caps.reasonCode,
                "message": caps.reason or "Voice Design is unavailable.",
            },
        )

    try:
        result = await orchestrator.generate_previews(
            prompt=req.prompt,
            language=req.language,
            preview_text=req.previewText,
            count=req.count,
            attributes={k: v for k, v in (req.attributes or {}).items() if v is not None},
        )
    except Exception as exc:
        logger.exception("Voice Design preview generation failed")
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "VOICE_DESIGN_PREVIEW_FAILED", "message": str(exc)},
        ) from exc

    return VoiceDesignPreviewResponse(
        sessionId=result.session_id,
        compiledInstruction=result.compiled_instruction,
        candidates=[
            {"id": c["id"], "audioUrl": c["audioUrl"]} for c in result.candidates
        ],
    )


@router.get(
    "/tts/voice-design/sessions/{session_id}",
    response_model=VoiceDesignSessionResponse,
)
async def get_voice_design_session(
    session_id: str,
):
    """Inspect an active or committed preview session."""
    session = load_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "VOICE_DESIGN_SESSION_NOT_FOUND", "message": "Session not found."},
        )

    base_url = f"/api/v1/tts/voice-design/sessions/{session.id}/candidates"
    return VoiceDesignSessionResponse(
        sessionId=session.id,
        compiledInstruction=session.compiled_instruction,
        previewText=session.preview_text,
        language=session.language,
        status=session.status,
        candidates=[
            {"id": c.id, "audioUrl": f"{base_url}/{c.id}/audio"} for c in session.candidates
        ],
    )


@router.get(
    "/tts/voice-design/sessions/{session_id}/candidates/{candidate_id}/audio"
)
async def get_voice_design_candidate_audio(
    session_id: str,
    candidate_id: str,
):
    """Stream a candidate preview WAV."""
    audio_path = get_candidate_audio_path(session_id, candidate_id)
    if audio_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "VOICE_DESIGN_CANDIDATE_NOT_FOUND", "message": "Candidate audio not found."},
        )

    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"voice-design-{session_id}-{candidate_id}.wav",
    )


@router.post(
    "/tts/voice-design/sessions/{session_id}/commit",
    status_code=status.HTTP_201_CREATED,
    response_model=VoiceDesignCommitResponse,
)
async def commit_voice_design(
    session_id: str,
    req: VoiceDesignCommitRequest,
    request: Request = None,  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    orchestrator: VoiceDesignOrchestrator = Depends(_get_orchestrator),  # noqa: B008
):
    """Freeze the selected candidate into a reusable OmniVoice voice."""
    check_request_feature(request, "voice_design")
    check_request_feature(request, "custom_voices")
    caps = await voice_design_capabilities()
    if not caps.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": caps.reasonCode,
                "message": caps.reason or "Voice Design is unavailable.",
            },
        )

    entitlement = getattr(request.state, "entitlement", None)
    license_entitlement_id = entitlement.id if entitlement else None

    try:
        result = await orchestrator.commit_voice(
            session_id=session_id,
            candidate_id=req.candidateId,
            display_name=req.displayName,
            session=session,
            license_entitlement_id=license_entitlement_id,
        )
    except Exception as exc:
        logger.exception("Voice Design commit failed")
        if isinstance(exc, HTTPException):
            raise
        detail: dict
        if hasattr(exc, "code"):
            detail = {"code": exc.code, "message": str(exc)}
        else:
            detail = {"code": "VOICE_DESIGN_COMMIT_FAILED", "message": str(exc)}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc

    return VoiceDesignCommitResponse(
        voiceId=result.voice_id,
        displayName=result.display_name,
        providerId=result.provider_id,
        engineId=result.engine_id,
        voiceKind=result.voice_kind,
        status=result.status,
    )
