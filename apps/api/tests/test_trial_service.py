import pytest

from app.exceptions import TrialNotAllowedError
from app.services.trial_domain import (
    TRIAL_DURATION_SECONDS,
    FakeTrialClock,
    TrialStatus,
    create_trial_state,
)
from app.services.trial_service import TrialService
from app.services.trial_storage import TrialStateRepository


def test_trial_service_refreshes_last_seen_and_blocks_expired_state(tmp_path) -> None:
    clock = FakeTrialClock(1_000)
    repository = TrialStateRepository(tmp_path / "trial-state-v1.json", b"k" * 32)
    repository.write(create_trial_state(first_run_at=1_000, install_id="install-1"))
    service = TrialService(repository=repository, clock=clock)

    clock.advance(TRIAL_DURATION_SECONDS)
    status = service.get_status()

    assert status.status is TrialStatus.EXPIRED
    assert status.remaining_seconds == 0
    with pytest.raises(TrialNotAllowedError) as error:
        service.assert_synthesis_allowed()
    assert error.value.code == "TRIAL_EXPIRED"


def test_trial_service_allows_active_state(tmp_path) -> None:
    clock = FakeTrialClock(1_000)
    repository = TrialStateRepository(tmp_path / "trial-state-v1.json", b"k" * 32)
    repository.write(create_trial_state(first_run_at=1_000, install_id="install-1"))
    service = TrialService(repository=repository, clock=clock)

    service.assert_synthesis_allowed()

    assert repository.read().last_seen_at == 1_000
