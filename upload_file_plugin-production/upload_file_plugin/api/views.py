from ..models import UploadedFile
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..utils import get_serialized_uploaded_files_for_objects


class GetFileFromDBAPIView(APIView):
    permission_classes = [IsAuthenticated]
    queryset = UploadedFile.objects.none()

    def post(self, request, *args, **kwargs):
        data = request.data
        objectIdList = data.get('objectIdList')
        modelName = data.get('modelName')

        files_data = get_serialized_uploaded_files_for_objects(objectIdList, modelName)

        return Response({
            'status': 'success',
            'files': files_data,
            'count': len(files_data)
        }, status=status.HTTP_200_OK)
