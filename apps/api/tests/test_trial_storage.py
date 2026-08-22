import json

import pytest

from app.services.trial_domain import TRIAL_DURATION_SECONDS, create_trial_state
from app.services.trial_storage import (
    TrialStateCorrupted,
    TrialStateRepository,
    merge_trial_states,
)


def test_mirror_round_trip_and_atomic_file_shape(tmp_path) -> None:
    repository = TrialStateRepository(tmp_path / "trial-state-v1.json", b"k" * 32)
    state = create_trial_state(first_run_at=100, install_id="install-1")

    repository.write(state)

    assert repository.read() == state
    payload = json.loads((tmp_path / "trial-state-v1.json").read_text())
    assert set(payload) == {"payload", "mac"}
    assert payload["payload"]["expires_at"] == 100 + TRIAL_DURATION_SECONDS


def test_mirror_tampering_is_corrupted(tmp_path) -> None:
    path = tmp_path / "trial-state-v1.json"
    repository = TrialStateRepository(path, b"k" * 32)
    repository.write(create_trial_state(first_run_at=100, install_id="install-1"))
    payload = json.loads(path.read_text())
    payload["payload"]["first_run_at"] = 0
    path.write_text(json.dumps(payload))

    with pytest.raises(TrialStateCorrupted):
        repository.read()


def test_missing_mirror_is_distinct_from_corruption(tmp_path) -> None:
    repository = TrialStateRepository(tmp_path / "trial-state-v1.json", b"k" * 32)

    assert repository.read() is None


def test_reconciliation_never_chooses_more_trial_time() -> None:
    secure = create_trial_state(first_run_at=100, last_seen_at=500, install_id="secure")
    mirror = create_trial_state(first_run_at=200, last_seen_at=900, install_id="mirror")

    merged = merge_trial_states(secure, mirror)

    assert merged.install_id == "secure"
    assert merged.first_run_at == 100
    assert merged.last_seen_at == 900
    assert merged.expires_at == secure.expires_at
