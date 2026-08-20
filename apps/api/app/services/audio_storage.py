from pathlib import Path

import httpx

from app.exceptions import TTSJobError

ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/x-mpeg",
    "audio/mp4",
    "audio/wav",
    "application/octet-stream",
    "video/mp4",
}
PROVIDER_MP3_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/x-mpeg",
    "application/octet-stream",
}
MP4_CONTENT_TYPES = {"audio/mp4", "video/mp4"}

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=10.0,
            pool=10.0,
        )
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=50,
        )
        _http_client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            max_redirects=5,
        )
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None


def _has_mp3_signature(path: Path) -> bool:
    with path.open("rb") as source:
        header = source.read(12)
    if header.startswith(b"ID3"):
        return True
    return len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0


def _has_mp4_signature(path: Path) -> bool:
    with path.open("rb") as source:
        header = source.read(12)
    return len(header) >= 8 and header[4:8] == b"ftyp"


def _has_wav_signature(path: Path) -> bool:
    with path.open("rb") as source:
        header = source.read(12)
    return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"


def validate_audio_file(path: Path, *, mime_type: str) -> int:
    if mime_type not in ALLOWED_CONTENT_TYPES:
        raise TTSJobError(
            code="AUDIO_INVALID_CONTENT",
            message=f"Unsupported audio MIME type: {mime_type}",
            retryable=False,
        )
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise TTSJobError(
            code="STORAGE_ERROR",
            message=str(exc),
            retryable=False,
        ) from exc
    if mime_type in MP4_CONTENT_TYPES:
        has_valid_signature = _has_mp4_signature(path)
    elif mime_type == "audio/wav":
        has_valid_signature = _has_wav_signature(path)
    else:
        has_valid_signature = _has_mp3_signature(path)
    if size <= 0 or not has_valid_signature:
        raise TTSJobError(
            code="AUDIO_INVALID_CONTENT",
            message="Audio output is empty or has an invalid signature.",
            retryable=False,
        )
    return size


async def download_audio(
    *,
    url: str,
    destination: Path,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(".tmp")
    client = get_http_client()

    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            content_type = (
                response.headers.get("content-type", "").split(";")[0].lower()
            )
            if content_type and content_type not in ALLOWED_CONTENT_TYPES:
                raise ValueError(f"Unexpected content type: {content_type}")

            total = 0
            with temp_path.open("wb") as output:
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Audio file exceeds maximum size limit")
                    output.write(chunk)

        if total == 0:
            raise ValueError("Downloaded audio payload is empty")
        temp_path.replace(destination)
        return content_type or "audio/mpeg", total
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
