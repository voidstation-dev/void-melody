"""Stable error definitions for the OmniVoice runtime worker."""

from __future__ import annotations


class WorkerError(Exception):
    """Base exception for OmniVoice worker errors with stable error codes."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
        }


# Stable error code constants
OMNI_METHOD_NOT_FOUND = "OMNI_METHOD_NOT_FOUND"
OMNI_INVALID_REQUEST = "OMNI_INVALID_REQUEST"
OMNI_INVALID_PARAMS = "OMNI_INVALID_PARAMS"
OMNI_PACKAGE_NOT_INSTALLED = "OMNI_PACKAGE_NOT_INSTALLED"
OMNI_MODEL_NOT_INSTALLED = "OMNI_MODEL_NOT_INSTALLED"
OMNI_MODEL_LOAD_FAILED = "OMNI_MODEL_LOAD_FAILED"
OMNI_MODEL_NOT_LOADED = "OMNI_MODEL_NOT_LOADED"
OMNI_INFERENCE_FAILED = "OMNI_INFERENCE_FAILED"
OMNI_PROMPT_CREATE_FAILED = "OMNI_PROMPT_CREATE_FAILED"
OMNI_PROMPT_INVALID = "OMNI_PROMPT_INVALID"
OMNI_OUTPUT_PATH_INVALID = "OMNI_OUTPUT_PATH_INVALID"
OMNI_PATH_OUTSIDE_ROOT = "OMNI_PATH_OUTSIDE_ROOT"
OMNI_ALLOWED_ROOTS_NOT_CONFIGURED = "OMNI_ALLOWED_ROOTS_NOT_CONFIGURED"
OMNI_WORKER_INTERNAL_ERROR = "OMNI_WORKER_INTERNAL_ERROR"
