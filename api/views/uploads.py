from rest_framework import status
from rest_framework.views import APIView

from ..permissions import IsAuthenticatedUser
from ..responses import api_response
from ..serializers import GenericImageUploadSerializer
from ..services.media_service import upload_image
from ..utils import serialize_value


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        serializer = GenericImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload_result = upload_image(
            serializer.validated_data["image"],
            serializer.validated_data["folder"],
            field_name="image",
        )
        return api_response(
            data={"image": serialize_value(upload_result)},
            message="Image uploaded successfully.",
            status_code=status.HTTP_201_CREATED,
        )
