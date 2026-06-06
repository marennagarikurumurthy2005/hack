import cloudinary
import cloudinary.uploader
from django.conf import settings
from rest_framework.exceptions import ValidationError

from ..utils import utc_now


_cloudinary_configured = False


def configure_cloudinary() -> None:
    global _cloudinary_configured
    if _cloudinary_configured:
        return

    config = settings.CLOUDINARY_SETTINGS
    if not config["cloud_name"] or not config["api_key"] or not config["api_secret"]:
        raise ValidationError({"cloudinary": "Cloudinary credentials are missing from environment settings."})

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
        root_folder = settings.CLOUDINARY_SETTINGS["folder"]
        upload_result = cloudinary.uploader.upload(
            file_obj,
            folder=f"{root_folder}/{folder}",
            resource_type="image",
        )
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(
            {field_name: "Image upload failed. Check Cloudinary configuration and credentials."}
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
