from typing import Any

import httpx
import requests
from capcut_tts_api.exceptions import (
    CapCutAPIError,
    CapCutError,
    CapCutTaskError,
)

from app.exceptions import TTSJobError


def _retry_after_from_data(data: dict[str, Any]) -> float | None:
    for key in ("retry_after", "retryAfter", "retry_after_seconds"):
        value = data.get(key)
        if value is None:
            continue
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            continue
    return None


def map_provider_error(error: BaseException) -> TTSJobError:
    if isinstance(error, TTSJobError):
        return error
    if type(error).__name__ == "VoxCpmProviderError":
        # Explicit VoxCPM2 failure (voice missing, runtime busy, ...):
        # surfaced as PROVIDER_REJECTED with the provider's code attached —
        # never retried as a fallback to another provider.
        return TTSJobError(
            code="PROVIDER_REJECTED",
            message=f"[voxcpm2] {getattr(error, 'code', '')}: {error}",
            retryable=False,
        )
    if type(error).__name__ == "VoxCpmRuntimeError":
        code = getattr(error, "code", "")
        if code in ("VOXCPM_RUNTIME_TIMEOUT", "VOXCPM_RUNTIME_CRASHED"):
            return TTSJobError(
                code="PROVIDER_TIMEOUT",
                message=f"[voxcpm2] {error}",
                retryable=True,
            )
        return TTSJobError(
            code="PROVIDER_UNAVAILABLE",
            message=f"[voxcpm2] {error}",
            retryable=False,
        )
    if isinstance(error, (requests.Timeout, TimeoutError)):
        return TTSJobError(
            code="PROVIDER_TIMEOUT",
            message=str(error),
            retryable=True,
        )
    if isinstance(error, requests.ConnectionError):
        return TTSJobError(
            code="PROVIDER_UNAVAILABLE",
            message=str(error),
            retryable=True,
        )
    if isinstance(error, CapCutAPIError):
        retry_after = _retry_after_from_data(error.response_data)
        if error.status_code == 429:
            return TTSJobError(
                code="PROVIDER_RATE_LIMITED",
                message=str(error),
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if error.status_code >= 500:
            return TTSJobError(
                code="PROVIDER_UNAVAILABLE",
                message=str(error),
                retryable=True,
                retry_after_seconds=retry_after,
            )
        return TTSJobError(
            code="PROVIDER_REJECTED",
            message=str(error),
            retryable=False,
        )
    if isinstance(error, CapCutTaskError):
        if "timed out" in str(error).lower():
            return TTSJobError(
                code="PROVIDER_TIMEOUT",
                message=str(error),
                retryable=True,
            )
        return TTSJobError(
            code="PROVIDER_REJECTED",
            message=str(error),
            retryable=False,
        )
    if isinstance(error, (ValueError, TypeError)):
        return TTSJobError(
            code="PROVIDER_REJECTED",
            message=str(error),
            retryable=False,
        )
    if isinstance(error, CapCutError):
        return TTSJobError(
            code="PROVIDER_UNAVAILABLE",
            message=str(error),
            retryable=True,
        )
    return TTSJobError(
        code="INTERNAL_ERROR",
        message=str(error),
        retryable=False,
    )


def map_download_error(error: BaseException) -> TTSJobError:
    if isinstance(error, TTSJobError):
        return error
    if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
        return TTSJobError(
            code="AUDIO_DOWNLOAD_FAILED",
            message=str(error),
            retryable=True,
        )
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        retryable = status_code == 429 or status_code >= 500
        retry_after = error.response.headers.get("Retry-After")
        try:
            retry_after_seconds = (
                float(retry_after) if retry_after is not None else None
            )
        except ValueError:
            retry_after_seconds = None
        return TTSJobError(
            code="AUDIO_DOWNLOAD_FAILED",
            message=str(error),
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
        )
    if isinstance(error, ValueError):
        return TTSJobError(
            code="AUDIO_INVALID_CONTENT",
            message=str(error),
            retryable=False,
        )
    if isinstance(error, OSError):
        return TTSJobError(
            code="STORAGE_ERROR",
            message=str(error),
            retryable=False,
        )
    return TTSJobError(
        code="AUDIO_DOWNLOAD_FAILED",
        message=str(error),
        retryable=False,
    )


def calculate_retry_delay(
    *,
    attempt: int,
    base_delay_seconds: float,
    retry_after_seconds: float | None = None,
    jitter: float = 0.0,
) -> float:
    base = (
        retry_after_seconds
        if retry_after_seconds is not None
        else min(30.0, base_delay_seconds * (2**attempt))
    )
    return max(0.0, base) + max(0.0, jitter)
