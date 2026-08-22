"""Pure, UTC-based domain model for the temporary beta trial.

This module deliberately has no filesystem, database, FastAPI, or Tauri
dependencies. Persistence and reconciliation can therefore be tested without
waiting for wall-clock time or importing the API application.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from time import time
from typing import Protocol
from uuid import uuid4

TRIAL_SCHEMA_VERSION = 1
TRIAL_DURATION_SECONDS = 7 * 24 * 60 * 60
CLOCK_ROLLBACK_TOLERANCE_SECONDS = 5 * 60


class TrialStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRING = "EXPIRING"
    EXPIRED = "EXPIRED"
    CLOCK_TAMPERED = "CLOCK_TAMPERED"
    CORRUPTED = "CORRUPTED"


class WarningLevel(StrEnum):
    NONE = "NONE"
    FORTY_EIGHT_HOURS = "FORTY_EIGHT_HOURS"
    TWENTY_FOUR_HOURS = "TWENTY_FOUR_HOURS"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class TrialState:
    schema_version: int
    install_id: str
    first_run_at: int
    last_seen_at: int
    expires_at: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "schema_version": self.schema_version,
            "install_id": self.install_id,
            "first_run_at": self.first_run_at,
            "last_seen_at": self.last_seen_at,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True, slots=True)
class TrialEvaluation:
    status: TrialStatus
    can_synthesize: bool
    first_run_at: int
    expires_at: int
    remaining_seconds: int
    warning_level: WarningLevel
    effective_now: int
    state: TrialState


class TrialClock(Protocol):
    def now(self) -> int: ...


class SystemUtcClock:
    def now(self) -> int:
        return int(time())


class FakeTrialClock:
    def __init__(self, current_time: int):
        self._current_time = current_time

    def now(self) -> int:
        return self._current_time

    def set(self, current_time: int) -> None:
        self._current_time = current_time

    def advance(self, seconds: int) -> None:
        self._current_time += seconds


def create_trial_state(
    *,
    first_run_at: int,
    install_id: str | None = None,
    last_seen_at: int | None = None,
) -> TrialState:
    return TrialState(
        schema_version=TRIAL_SCHEMA_VERSION,
        install_id=install_id or str(uuid4()),
        first_run_at=first_run_at,
        last_seen_at=last_seen_at if last_seen_at is not None else first_run_at,
        expires_at=first_run_at + TRIAL_DURATION_SECONDS,
    )


def touch_trial_state(state: TrialState, *, now: int) -> TrialState:
    """Record the furthest observed time without moving expiration forward."""

    if now <= state.last_seen_at:
        return state
    return replace(state, last_seen_at=now)


def evaluate_trial(
    state: TrialState,
    *,
    now: int,
    rollback_tolerance_seconds: int = CLOCK_ROLLBACK_TOLERANCE_SECONDS,
) -> TrialEvaluation:
    """Derive fail-closed status from a persisted state and UTC epoch now."""

    if now < state.last_seen_at - rollback_tolerance_seconds:
        return TrialEvaluation(
            status=TrialStatus.CLOCK_TAMPERED,
            can_synthesize=False,
            first_run_at=state.first_run_at,
            expires_at=state.expires_at,
            remaining_seconds=max(0, state.expires_at - state.last_seen_at),
            warning_level=WarningLevel.EXPIRED
            if state.expires_at <= state.last_seen_at
            else WarningLevel.TWENTY_FOUR_HOURS
            if state.expires_at - state.last_seen_at <= 24 * 60 * 60
            else WarningLevel.FORTY_EIGHT_HOURS,
            effective_now=state.last_seen_at,
            state=state,
        )

    effective_now = max(now, state.last_seen_at)
    next_state = touch_trial_state(state, now=now)
    remaining = state.expires_at - effective_now
    if remaining <= 0:
        status = TrialStatus.EXPIRED
        warning = WarningLevel.EXPIRED
        can_synthesize = False
    elif remaining <= 24 * 60 * 60:
        status = TrialStatus.EXPIRING
        warning = WarningLevel.TWENTY_FOUR_HOURS
        can_synthesize = True
    elif remaining <= 48 * 60 * 60:
        status = TrialStatus.EXPIRING
        warning = WarningLevel.FORTY_EIGHT_HOURS
        can_synthesize = True
    else:
        status = TrialStatus.ACTIVE
        warning = WarningLevel.NONE
        can_synthesize = True

    return TrialEvaluation(
        status=status,
        can_synthesize=can_synthesize,
        first_run_at=state.first_run_at,
        expires_at=state.expires_at,
        remaining_seconds=max(0, remaining),
        warning_level=warning,
        effective_now=effective_now,
        state=next_state,
    )
