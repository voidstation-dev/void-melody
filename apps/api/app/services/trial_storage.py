"""Crash-safe, HMAC-protected app-data mirror for the trial state."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path

from app.services.trial_domain import (
    TRIAL_DURATION_SECONDS,
    TRIAL_SCHEMA_VERSION,
    TrialState,
)


class TrialStateCorrupted(ValueError):
    pass


def decode_integrity_key(value: str | bytes | None) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value if value else None
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise TrialStateCorrupted("Invalid trial integrity key") from exc
    return decoded or None


class TrialStateRepository:
    def __init__(self, path: Path, integrity_key: bytes):
        if len(integrity_key) < 32:
            raise ValueError("Trial integrity key must be at least 256 bits")
        self.path = Path(path)
        self.integrity_key = integrity_key

    @staticmethod
    def _canonical_payload(state: TrialState) -> bytes:
        return json.dumps(
            state.as_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

    def _mac(self, state: TrialState) -> str:
        digest = hmac.new(
            self.integrity_key,
            self._canonical_payload(state),
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def _parse_state(payload: object) -> TrialState:
        if not isinstance(payload, dict):
            raise TrialStateCorrupted("Trial payload is not an object")
        try:
            state = TrialState(
                schema_version=int(payload["schema_version"]),
                install_id=str(payload["install_id"]),
                first_run_at=int(payload["first_run_at"]),
                last_seen_at=int(payload["last_seen_at"]),
                expires_at=int(payload["expires_at"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TrialStateCorrupted("Trial payload is incomplete") from exc
        if (
            state.schema_version != TRIAL_SCHEMA_VERSION
            or not state.install_id
            or state.first_run_at < 0
            or state.last_seen_at < state.first_run_at
            or state.expires_at != state.first_run_at + TRIAL_DURATION_SECONDS
        ):
            raise TrialStateCorrupted("Trial payload failed validation")
        return state

    def read(self) -> TrialState | None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise TrialStateCorrupted("Trial mirror could not be read") from exc
        try:
            envelope = json.loads(raw)
            payload = envelope["payload"]
            supplied_mac = str(envelope["mac"])
            state = self._parse_state(payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, TrialStateCorrupted):
                raise
            raise TrialStateCorrupted("Trial mirror is malformed") from exc
        expected_mac = self._mac(state)
        if not hmac.compare_digest(supplied_mac, expected_mac):
            raise TrialStateCorrupted("Trial mirror integrity check failed")
        return state

    def write(self, state: TrialState) -> None:
        self._parse_state(state.as_dict())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "payload": state.as_dict(),
            "mac": self._mac(state),
        }
        encoded = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
            try:
                directory_fd = os.open(self.path.parent, os.O_DIRECTORY)
            except (AttributeError, OSError):
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            Path(temporary_name).unlink(missing_ok=True)


def merge_trial_states(secure: TrialState, mirror: TrialState) -> TrialState:
    """Merge mismatches conservatively, using secure identity and oldest time."""

    first_run_at = min(secure.first_run_at, mirror.first_run_at)
    last_seen_at = max(secure.last_seen_at, mirror.last_seen_at)
    return TrialState(
        schema_version=TRIAL_SCHEMA_VERSION,
        install_id=secure.install_id,
        first_run_at=first_run_at,
        last_seen_at=last_seen_at,
        expires_at=first_run_at + TRIAL_DURATION_SECONDS,
    )
