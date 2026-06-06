from rest_framework import status
from rest_framework.response import Response

from .utils import build_pagination_payload


def api_response(
    data=None,
    message: str = "Request processed successfully.",
    status_code: int = status.HTTP_200_OK,
    **extra,
):
    payload = {"message": message}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return Response(payload, status=status_code)


def paginated_response(items, page: int, page_size: int, total: int, message: str = "Request processed successfully."):
    return api_response(
        data={
            "items": items,
            "pagination": build_pagination_payload(page, page_size, total),
        },
        message=message,
    )
