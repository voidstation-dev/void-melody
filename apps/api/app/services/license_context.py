"""Request-scoped license entitlement passed by the local web client."""

from contextvars import ContextVar, Token

_runtime_license_key: ContextVar[str | None] = ContextVar(
    "runtime_license_key",
    default=None,
)


def set_runtime_license_key(value: str | None) -> Token[str | None]:
    return _runtime_license_key.set(value)


def reset_runtime_license_key(token: Token[str | None]) -> None:
    _runtime_license_key.reset(token)


def get_runtime_license_key() -> str | None:
    return _runtime_license_key.get()
