from rest_framework import serializers


def raise_serializer_validation_error(exc):
    """Giữ nguyên field errors của Django khi trả lỗi qua DRF."""
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)
    raise serializers.ValidationError(exc.messages)
