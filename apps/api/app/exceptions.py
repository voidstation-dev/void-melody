class TTSJobError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


class TrialNotAllowedError(Exception):
    """Raised when a new compute action is not authorized by the trial."""

    def __init__(self, *, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
