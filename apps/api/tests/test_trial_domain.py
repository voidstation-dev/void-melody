from datetime import datetime, timezone

import pytest

from app.services.trial_domain import (
    CLOCK_ROLLBACK_TOLERANCE_SECONDS,
    TRIAL_DURATION_SECONDS,
    FakeTrialClock,
    TrialState,
    TrialStatus,
    WarningLevel,
    create_trial_state,
    evaluate_trial,
)


def epoch(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def test_trial_uses_exactly_seven_days_and_utc_epoch() -> None:
    first_run = epoch("2026-08-22T00:00:00")
    state = create_trial_state(first_run_at=first_run, install_id="install-1")

    assert TRIAL_DURATION_SECONDS == 7 * 24 * 60 * 60
    assert state.expires_at == first_run + TRIAL_DURATION_SECONDS
    assert evaluate_trial(state, now=first_run + 4 * 24 * 60 * 60).status is TrialStatus.ACTIVE
    assert evaluate_trial(state, now=first_run + 4 * 24 * 60 * 60).warning_level is WarningLevel.NONE


@pytest.mark.parametrize(
    ("offset", "status", "warning"),
    [
        (5 * 24 * 60 * 60, TrialStatus.EXPIRING, WarningLevel.FORTY_EIGHT_HOURS),
        (6 * 24 * 60 * 60, TrialStatus.EXPIRING, WarningLevel.TWENTY_FOUR_HOURS),
        (TRIAL_DURATION_SECONDS - 1, TrialStatus.EXPIRING, WarningLevel.TWENTY_FOUR_HOURS),
        (TRIAL_DURATION_SECONDS, TrialStatus.EXPIRED, WarningLevel.EXPIRED),
        (TRIAL_DURATION_SECONDS + 24 * 60 * 60, TrialStatus.EXPIRED, WarningLevel.EXPIRED),
    ],
)
def test_trial_status_boundaries(offset: int, status: TrialStatus, warning: WarningLevel) -> None:
    state = create_trial_state(first_run_at=1_000, install_id="install-1")

    result = evaluate_trial(state, now=1_000 + offset)

    assert result.status is status
    assert result.warning_level is warning


def test_fake_clock_makes_expiration_deterministic() -> None:
    clock = FakeTrialClock(10_000)
    state = create_trial_state(first_run_at=clock.now(), install_id="install-1")

    clock.advance(TRIAL_DURATION_SECONDS - 1)
    assert evaluate_trial(state, now=clock.now()).can_synthesize
    clock.advance(1)
    assert not evaluate_trial(state, now=clock.now()).can_synthesize


def test_large_clock_rollback_fails_closed_without_extending_trial() -> None:
    state = create_trial_state(first_run_at=1_000, install_id="install-1", last_seen_at=50_000)

    result = evaluate_trial(state, now=50_000 - CLOCK_ROLLBACK_TOLERANCE_SECONDS - 1)

    assert result.status is TrialStatus.CLOCK_TAMPERED
    assert not result.can_synthesize
    assert result.remaining_seconds == max(0, state.expires_at - state.last_seen_at)


def test_small_clock_rollback_is_clamped_to_last_seen() -> None:
    state = create_trial_state(first_run_at=1_000, install_id="install-1", last_seen_at=10_000)

    result = evaluate_trial(
        state,
        now=10_000 - CLOCK_ROLLBACK_TOLERANCE_SECONDS,
    )

    assert result.status is TrialStatus.ACTIVE
    assert result.effective_now == state.last_seen_at
    assert result.remaining_seconds == state.expires_at - state.last_seen_at


def test_timezone_is_irrelevant_when_callers_supply_utc_epoch() -> None:
    state = TrialState(
        schema_version=1,
        install_id="install-1",
        first_run_at=1_000,
        last_seen_at=1_000,
        expires_at=1_000 + TRIAL_DURATION_SECONDS,
    )

    assert evaluate_trial(state, now=1_000 + 60).remaining_seconds == TRIAL_DURATION_SECONDS - 60
