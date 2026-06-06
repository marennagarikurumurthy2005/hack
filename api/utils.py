import json
from datetime import datetime, timezone
from math import ceil
from uuid import uuid4

from bson import ObjectId
from rest_framework.exceptions import ValidationError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def maybe_object_id(value):
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def parse_object_id(value, field_name: str = "id") -> ObjectId:
    object_id = maybe_object_id(value)
    if object_id is None:
        raise ValidationError({field_name: "Invalid identifier."})
    return object_id


def generate_reference(prefix: str) -> str:
    return f"{prefix}-{utc_now():%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}"


def serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        serialized = {}
        for key, item in value.items():
            output_key = "id" if key == "_id" else key
            serialized[output_key] = serialize_value(item)
        return serialized
    return value


def parse_list_input(value):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in value.split(",") if item.strip()]
    return [value]


def parse_pagination_params(query_params, default_page_size: int = 10, max_page_size: int = 100):
    try:
        page = int(query_params.get("page", 1))
        page_size = int(query_params.get("page_size", default_page_size))
    except (TypeError, ValueError) as exc:
        raise ValidationError({"pagination": "Page and page_size must be integers."}) from exc

    if page < 1:
        raise ValidationError({"page": "Page must be at least 1."})
    if page_size < 1 or page_size > max_page_size:
        raise ValidationError({"page_size": f"page_size must be between 1 and {max_page_size}."})

    return page, page_size


def build_pagination_payload(page: int, page_size: int, total: int):
    total_pages = ceil(total / page_size) if page_size else 1
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }


def parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}
