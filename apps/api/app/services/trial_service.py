"""Backend trial authority and the narrow guard used by compute paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.config import settings
from app.exceptions import TrialNotAllowedError
from app.services.trial_domain import (
    FakeTrialClock,
    SystemUtcClock,
    TrialClock,
    TrialEvaluation,
    TrialState,
    TrialStatus,
    WarningLevel,
    evaluate_trial,
)
from app.services.trial_storage import (
    TrialStateCorrupted,
    TrialStateRepository,
    decode_integrity_key,
)


@dataclass(frozen=True, slots=True)
class TrialStatusSnapshot:
    status: TrialStatus
    can_synthesize: bool
    first_run_at: int | None
    expires_at: int | None
    remaining_seconds: int
    warning_level: WarningLevel
    override: str | None = None

    @classmethod
    def from_evaluation(cls, evaluation: TrialEvaluation) -> "TrialStatusSnapshot":
        return cls(
            status=evaluation.status,
            can_synthesize=evaluation.can_synthesize,
            first_run_at=evaluation.first_run_at,
            expires_at=evaluation.expires_at,
            remaining_seconds=evaluation.remaining_seconds,
            warning_level=evaluation.warning_level,
        )


class EntitlementService(Protocol):
    """Stable seam for replacing local trial with a paid/server entitlement."""

    def get_status(self) -> TrialStatusSnapshot: ...

    def assert_synthesis_allowed(self) -> TrialStatusSnapshot: ...


class TrialService:
    def __init__(
        self,
        *,
        repository: TrialStateRepository,
        clock: TrialClock | None = None,
    ):
        self.repository = repository
        self.clock = clock or SystemUtcClock()

    def _evaluation(self) -> TrialEvaluation:
        state = self.repository.read()
        if state is None:
            raise TrialStateCorrupted("Trial state is missing")
        evaluation = evaluate_trial(state, now=self.clock.now())
        if evaluation.state != state:
            self.repository.write(evaluation.state)
        return evaluation

    def get_status(self) -> TrialStatusSnapshot:
        try:
            return TrialStatusSnapshot.from_evaluation(self._evaluation())
        except TrialStateCorrupted:
            return TrialStatusSnapshot(
                status=TrialStatus.CORRUPTED,
                can_synthesize=False,
                first_run_at=None,
                expires_at=None,
                remaining_seconds=0,
                warning_level=WarningLevel.EXPIRED,
            )

    def assert_synthesis_allowed(self) -> TrialStatusSnapshot:
        snapshot = self.get_status()
        if snapshot.can_synthesize:
            return snapshot
        code = {
            TrialStatus.EXPIRED: "TRIAL_EXPIRED",
            TrialStatus.CLOCK_TAMPERED: "TRIAL_CLOCK_TAMPERED",
            TrialStatus.CORRUPTED: "TRIAL_STATE_CORRUPTED",
        }.get(snapshot.status, "TRIAL_STATE_CORRUPTED")
        raise TrialNotAllowedError(
            code=code,
            message={
                "TRIAL_EXPIRED": "The seven-day trial has expired.",
                "TRIAL_CLOCK_TAMPERED": "System clock rollback was detected.",
                "TRIAL_STATE_CORRUPTED": "Trial state could not be verified.",
            }[code],
        )


class DevelopmentTrialService:
    """Explicit development-only bypass; no persisted reset exists in release."""

    def __init__(self, clock: TrialClock | None = None):
        self.clock = clock or SystemUtcClock()

    def get_status(self) -> TrialStatusSnapshot:
        now = self.clock.now()
        return TrialStatusSnapshot(
            status=TrialStatus.ACTIVE,
            can_synthesize=True,
            first_run_at=now,
            expires_at=now,
            remaining_seconds=-1,
            warning_level=WarningLevel.NONE,
            override="disabled",
        )

    def assert_synthesis_allowed(self) -> TrialStatusSnapshot:
        return self.get_status()


def get_runtime_trial_service() -> TrialService | DevelopmentTrialService:
    """Build the service from runtime configuration without frontend input."""

    is_development = settings.app_env.lower() == "development"
    if is_development and settings.trial_mode.lower() == "disabled":
        return DevelopmentTrialService()
    key = decode_integrity_key(settings.trial_integrity_key)
    if is_development and settings.trial_mode.lower() == "auto" and key is None:
        return DevelopmentTrialService()
    if key is None:
        # Production without a Tauri bootstrap is intentionally fail-closed.
        key = b"invalid-trial-runtime-key"
    return TrialService(
        repository=TrialStateRepository(settings.trial_state_path, key),
    )


def require_synthesis() -> TrialStatusSnapshot:
    return get_runtime_trial_service().assert_synthesis_allowed()
