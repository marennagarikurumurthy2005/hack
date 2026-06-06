from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password

from ..constants import ROLE_SUPER_ADMIN
from ..utils import serialize_value, utc_now


def hash_password(raw_password: str) -> str:
    return make_password(raw_password)


def verify_password(raw_password: str, encoded_password: str) -> bool:
    return check_password(raw_password, encoded_password)


def generate_access_token(user_document: dict) -> str:
    now = utc_now()
    expiry = now + timedelta(minutes=settings.JWT_SETTINGS["ACCESS_TOKEN_LIFETIME_MINUTES"])
    payload = {
        "sub": str(user_document["_id"]),
        "role": user_document["role"],
        "verification_status": user_document["verification_status"],
        "full_name": user_document["full_name"],
        "email": user_document["email"],
        "iat": now,
        "exp": expiry,
    }
    return jwt.encode(
        payload,
        settings.JWT_SETTINGS["SECRET_KEY"],
        algorithm=settings.JWT_SETTINGS["ALGORITHM"],
    )


def decode_access_token(token: str):
    return jwt.decode(
        token,
        settings.JWT_SETTINGS["SECRET_KEY"],
        algorithms=[settings.JWT_SETTINGS["ALGORITHM"]],
    )


def mask_sensitive_value(value: str | None, visible_digits: int = 4):
    if not value:
        return value
    text = str(value)
    if len(text) <= visible_digits:
        return "*" * len(text)
    return f"{'*' * (len(text) - visible_digits)}{text[-visible_digits:]}"


def serialize_user_for_response(user_document: dict, include_confidential: bool = False):
    payload = serialize_value(user_document)
    payload.pop("password_hash", None)

    if not include_confidential:
        government_id_number = payload.pop("government_id_number", None)
        employee_id = payload.pop("employee_id", None)
        if government_id_number:
            payload["government_id_number_masked"] = mask_sensitive_value(government_id_number)
        if employee_id:
            payload["employee_id_masked"] = mask_sensitive_value(employee_id)
    return payload


def serialize_user_for_public(user_document: dict):
    payload = serialize_user_for_response(user_document, include_confidential=False)
    allowed_keys = {
        "id",
        "full_name",
        "role",
        "village",
        "ward_number",
        "district",
        "state",
    }
    return {key: payload.get(key) for key in allowed_keys if payload.get(key) not in (None, "", [])}


def build_actor_snapshot(user):
    if isinstance(user, dict):
        identifier = str(user.get("_id"))
        full_name = user.get("full_name", "")
        role = user.get("role", "")
    else:
        identifier = str(getattr(user, "id", ""))
        full_name = getattr(user, "full_name", "")
        role = getattr(user, "role", "")

    return {
        "id": identifier,
        "full_name": full_name,
        "role": role,
        "is_super_admin": role == ROLE_SUPER_ADMIN,
    }
