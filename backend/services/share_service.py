"""Pure helpers for share-token hashing, expiry, and trip access decisions."""

import hashlib
from datetime import datetime
from typing import Any


def hash_share_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_share_token_active(share_token: Any, now: datetime | None = None) -> bool:
    if share_token is None or getattr(share_token, "revoked_at", None) is not None:
        return False
    expires_at = getattr(share_token, "expires_at", None)
    return expires_at is not None and expires_at > (now or datetime.utcnow())


def is_trip_owner(trip: Any, user: dict | None) -> bool:
    return bool(user and getattr(trip, "user_id", None) == user.get("user_id"))


def can_read_trip(trip: Any, user: dict | None = None, share_token: Any = None) -> bool:
    return bool(
        getattr(trip, "is_public", 0) == 1
        or is_trip_owner(trip, user)
        or (
            is_share_token_active(share_token)
            and getattr(share_token, "trip_id", None) == getattr(trip, "id", None)
        )
    )

