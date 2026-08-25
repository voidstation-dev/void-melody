from fastapi import APIRouter

from app.api.v1 import (
    emotional_scripts,
    health,
    runtimes,
    tts_batches,
    tts_jobs,
    voices,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(tts_jobs.router, tags=["TTS Jobs"])
api_router.include_router(tts_batches.router, tags=["TTS Batches"])
api_router.include_router(voices.router, tags=["Voices"])
api_router.include_router(runtimes.router, tags=["Runtimes"])
api_router.include_router(emotional_scripts.router, tags=["Emotional Scripts"])
