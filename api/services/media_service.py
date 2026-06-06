import cloudinary
import cloudinary.exceptions
import cloudinary.uploader
from django.conf import settings
from rest_framework.exceptions import ValidationError
from urllib.parse import urlparse

from ..utils import utc_now


_cloudinary_configured = False


def _resolve_cloudinary_config() -> dict:
    config = settings.CLOUDINARY_SETTINGS
    cloudinary_url = config.get("cloudinary_url", "").strip()

    cloud_name = config.get("cloud_name", "").strip()
    api_key = config.get("api_key", "").strip()
    api_secret = config.get("api_secret", "").strip()

    if (not cloud_name or not api_key or not api_secret) and cloudinary_url:
        parsed = urlparse(cloudinary_url)
        if parsed.scheme == "cloudinary" and parsed.hostname:
            cloud_name = cloud_name or parsed.hostname.strip()
            api_key = api_key or (parsed.username or "").strip()
            api_secret = api_secret or (parsed.password or "").strip()

    return {
        "cloud_name": cloud_name,
        "api_key": api_key,
        "api_secret": api_secret,
        "folder": config.get("folder", "village-governance").strip() or "village-governance",
    }


def configure_cloudinary() -> None:
    global _cloudinary_configured
    if _cloudinary_configured:
        return

    config = _resolve_cloudinary_config()
    if not config["cloud_name"] or not config["api_key"] or not config["api_secret"]:
        raise ValidationError(
            {
                "cloudinary": (
                    "Cloudinary credentials are missing from environment settings. "
                    "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, "
                    "or CLOUDINARY_URL."
                )
            }
        )

    cloudinary.config(
        cloud_name=config["cloud_name"],
        api_key=config["api_key"],
        api_secret=config["api_secret"],
        secure=True,
    )
    _cloudinary_configured = True


def upload_image(file_obj, folder: str, field_name: str = "image"):
    if not getattr(file_obj, "content_type", "").startswith("image/"):
        raise ValidationError({field_name: "Only image uploads are supported."})

    try:
        configure_cloudinary()
        root_folder = _resolve_cloudinary_config()["folder"]
        upload_result = cloudinary.uploader.upload(
            file_obj,
            folder=f"{root_folder}/{folder}",
            resource_type="image",
        )
    except ValidationError:
        raise
    except cloudinary.exceptions.Error as exc:
        raise ValidationError({field_name: f"Cloudinary upload failed: {exc}"}) from exc
    except Exception as exc:
        raise ValidationError(
            {field_name: f"Image upload failed. Check Cloudinary configuration and credentials. {exc}"}
        ) from exc

    return {
        "public_id": upload_result.get("public_id"),
        "url": upload_result.get("secure_url"),
        "width": upload_result.get("width"),
        "height": upload_result.get("height"),
        "format": upload_result.get("format"),
        "bytes": upload_result.get("bytes"),
        "uploaded_at": utc_now(),
    }
