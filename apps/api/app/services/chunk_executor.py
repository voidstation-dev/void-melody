import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from app.services.prepared_voice import PreparedVoice


@dataclass(frozen=True)
class JobSnapshot:
    id: str
    voice_type: str
    resource_id: str | None
    rate: float
    style: str | None = None
    provider_id: str = "capcut"
    reference_audio_path: str | None = None
    prompt_text: str | None = None
    voice_revision: str = "v1"
    prepared_voice: PreparedVoice | None = None
    speaker_emb: Any | None = None
    ref_codes: Any | None = None
    clone_mode: str = "fidelity"
    profile_format_version: str = "reference-v1"
    output_format: str = "mp3"


@dataclass(frozen=True)
class ChunkResult:
    index: int
    path: Path
    raw_response: dict
    mime_type: str
    size: int
    owned_by_job: bool = True


class ChunkLimitExceeded(ValueError):
    def __init__(self, *, actual: int, maximum: int):
        super().__init__(f"The job creates {actual} chunks; maximum is {maximum}.")
        self.actual = actual
        self.maximum = maximum


def ensure_chunk_limit(chunks: Sequence[str], *, max_chunks: int) -> None:
    if len(chunks) > max_chunks:
        raise ChunkLimitExceeded(actual=len(chunks), maximum=max_chunks)


ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class _Failure:
    error: BaseException


async def execute_chunks_bounded(
    chunks: Sequence[str],
    *,
    concurrency: int,
    process_chunk: Callable[..., Awaitable[ResultT]],
    is_cancelled: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[ResultT]:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if not chunks:
        return

    next_index = 0
    input_lock = asyncio.Lock()
    output_queue: asyncio.Queue[ResultT | _Failure] = asyncio.Queue()

    async def worker() -> None:
        nonlocal next_index
        while True:
            async with input_lock:
                if next_index >= len(chunks):
                    return
                index = next_index
                next_index += 1
                text = chunks[index]

            try:
                if is_cancelled is not None:
                    cancelled = await is_cancelled()
                    if cancelled:
                        raise asyncio.CancelledError("Job was cancelled by user")

                result = await process_chunk(index=index, text=text)
            except BaseException as exc:  # noqa: BLE001
                await output_queue.put(_Failure(exc))
                return
            await output_queue.put(result)

    workers = [
        asyncio.create_task(worker(), name=f"tts-chunk-{index}")
        for index in range(min(concurrency, len(chunks)))
    ]

    try:
        for _ in range(len(chunks)):
            result = await output_queue.get()
            if isinstance(result, _Failure):
                raise result.error
            yield result
    finally:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
