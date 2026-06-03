from rest_framework import serializers
from ..models import UploadedFile

class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = [
            'id',
            'object_id',
            'model_name',
            'file_name'
        ]
