"""Minimal in-memory sliding-window rate limiter for login attempts, to
blunt credential-stuffing / brute-force attempts against /auth/login.

Deliberately simple for a single-process prototype: state is a plain dict,
not shared across workers or processes. A real multi-instance deployment
would move this to Redis (or similar) so all instances see the same
attempt counts -- noted as a limitation, not hidden.
"""

import time
from collections import defaultdict

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
LOCKOUT_SECONDS = 60

_failed_attempts: dict[str, list[float]] = defaultdict(list)
_locked_until: dict[str, float] = {}


def _key(identifier: str) -> str:
    return identifier.lower().strip()


def is_locked_out(identifier: str) -> float:
    """Returns seconds remaining if locked out, else 0."""
    key = _key(identifier)
    now = time.time()
    until = _locked_until.get(key)
    if until and until > now:
        return round(until - now, 1)
    if until and until <= now:
        _locked_until.pop(key, None)
        _failed_attempts[key] = []
    return 0


def record_failure(identifier: str) -> None:
    key = _key(identifier)
    now = time.time()
    _failed_attempts[key] = [t for t in _failed_attempts[key] if now - t < WINDOW_SECONDS]
    _failed_attempts[key].append(now)
    if len(_failed_attempts[key]) >= MAX_ATTEMPTS:
        _locked_until[key] = now + LOCKOUT_SECONDS


def record_success(identifier: str) -> None:
    key = _key(identifier)
    _failed_attempts[key] = []
    _locked_until.pop(key, None)
