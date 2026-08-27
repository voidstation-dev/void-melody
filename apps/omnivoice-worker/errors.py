"""Worker error codes and exception type."""

from __future__ import annotations


OMNI_ALLOWED_ROOTS_NOT_CONFIGURED = "OMNI_ALLOWED_ROOTS_NOT_CONFIGURED"
OMNI_PATH_OUTSIDE_ROOT = "OMNI_PATH_OUTSIDE_ROOT"
OMNI_INVALID_PARAMS = "OMNI_INVALID_PARAMS"
OMNI_INFERENCE_FAILED = "OMNI_INFERENCE_FAILED"
OMNI_METHOD_NOT_FOUND = "OMNI_METHOD_NOT_FOUND"
OMNI_PACKAGE_NOT_INSTALLED = "OMNI_PACKAGE_NOT_INSTALLED"
OMNI_PROMPT_INVALID = "OMNI_PROMPT_INVALID"


class WorkerError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
