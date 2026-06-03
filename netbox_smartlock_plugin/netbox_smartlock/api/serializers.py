from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers
from dcim.api.serializers import DeviceSerializer, LocationSerializer, RackSerializer, RegionSerializer, SiteSerializer
from dcim.models import Device, Location, Rack, Region, Site
from upload_file_plugin.services import sync_uploaded_files

from ..messages import (
    ACCESS_REQUEST_EDIT_LOCKED_MESSAGE,
    ACCESS_REQUEST_PERSON_EDIT_LOCKED_MESSAGE,
    ACCESS_REQUEST_PERSON_FILE_REQUIRED_MESSAGE,
    ACCESS_REQUEST_PERSON_SCOPE_DENIED_MESSAGE,
)
from ..models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock
from ..permissions import restrict_access_requests_for_user, user_can_access_request
from ..services import normalize_smartlock_api_data
from ..upload_files import files_for_object, upload_payload_has_valid_file
from .errors import raise_serializer_validation_error


def restrict_dcim_serializer_fields(fields, user, action="view"):
    """Áp object permission của NetBox lên các field DCIM trong API serializer."""
    if user is None:
        return

    for field_name in ("region_id", "site_id", "location_id", "rack_id"):
        field = fields.get(field_name)
        queryset = getattr(field, "queryset", None)
        if queryset is not None and hasattr(queryset, "restrict"):
            field.queryset = queryset.restrict(user, action)


class AssetGroupSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_smartlock-api:assetgroup-detail")

    class Meta:
        model = AssetGroup
        fields = (
            "id", "url", "display", "name", "slug", "code", "status",
            "exclude_from_visualization", "description", "tags", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "slug")


class AssetSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_smartlock-api:asset-detail")
    device = DeviceSerializer(nested=True, read_only=True)
    device_id = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all(), source="device", write_only=True)
    asset_group = AssetGroupSerializer(nested=True, read_only=True)
    asset_group_id = serializers.PrimaryKeyRelatedField(queryset=AssetGroup.objects.all(), source="asset_group", write_only=True)

    class Meta:
        model = Asset
        fields = (
            "id", "url", "display",
            "name", "code", "status", "description", "comments",
            "device", "device_id", "asset_group", "asset_group_id",
            "setup_date", "bought_date", "warranty_period", "warranty_expiration_date",
            "tags", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "code", "status", "device", "asset_group")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        request_user = getattr(request, "user", None)

        asset_group_queryset = AssetGroup.objects.filter(status=AssetGroup.STATUS_ACTIVE)
        if request_user is not None and hasattr(asset_group_queryset, "restrict"):
            asset_group_queryset = asset_group_queryset.restrict(request_user, "view")
        self.fields["asset_group_id"].queryset = asset_group_queryset

        device_queryset = Device.objects.all()
        if request_user is not None and hasattr(device_queryset, "restrict"):
            device_queryset = device_queryset.restrict(request_user, "view")
        if self.instance:
            device_queryset = device_queryset.filter(
                Q(smartlock_asset__isnull=True) | Q(pk=self.instance.device_id)
            )
        else:
            device_queryset = device_queryset.filter(smartlock_asset__isnull=True)
        self.fields["device_id"].queryset = device_queryset.distinct()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance or Asset()
        for key, value in attrs.items():
            setattr(instance, key, value)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise_serializer_validation_error(exc)
        return attrs


class SmartLockSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_smartlock-api:smartlock-detail")
    asset_group = AssetGroupSerializer(nested=True, read_only=True)
    asset_group_id = serializers.PrimaryKeyRelatedField(queryset=AssetGroup.objects.all(), source="asset_group", write_only=True)
    region = RegionSerializer(nested=True, read_only=True)
    region_id = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), source="region", write_only=True)
    site = SiteSerializer(nested=True, read_only=True)
    site_id = serializers.PrimaryKeyRelatedField(queryset=Site.objects.all(), source="site", write_only=True)
    location = LocationSerializer(nested=True, read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), source="location", write_only=True)
    rack = RackSerializer(nested=True, read_only=True, required=False)
    rack_id = serializers.PrimaryKeyRelatedField(queryset=Rack.objects.all(), source="rack", write_only=True, required=False, allow_null=True)

    class Meta:
        model = SmartLock
        fields = (
            "id", "url", "display",
            "name", "code", "status", "description", "comments",
            "asset_group", "asset_group_id",
            "device_type", "model", "serial", "manufacturer",
            "setup_date", "bought_date", "warranty_period", "warranty_expiration_date",
            "region", "region_id", "site", "site_id", "location", "location_id", "rack", "rack_id", "rack_face",
            "tags", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "code", "status", "site", "rack")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        asset_group_queryset = AssetGroup.objects.filter(status=AssetGroup.STATUS_ACTIVE)
        if request_user is not None and hasattr(asset_group_queryset, "restrict"):
            asset_group_queryset = asset_group_queryset.restrict(request_user, "view")
        self.fields["asset_group_id"].queryset = asset_group_queryset
        restrict_dcim_serializer_fields(self.fields, request_user)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        try:
            # Serializer validate trên candidate để partial update không làm lệch object đang có.
            return normalize_smartlock_api_data(self.instance, attrs)
        except DjangoValidationError as exc:
            raise_serializer_validation_error(exc)


class AccessRequestSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_smartlock-api:accessrequest-detail")
    region = RegionSerializer(nested=True, read_only=True, required=False)
    region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(),
        source="region",
        write_only=True,
        required=False,
        allow_null=True,
    )
    site = SiteSerializer(nested=True, read_only=True, required=False)
    site_id = serializers.PrimaryKeyRelatedField(
        queryset=Site.objects.all(),
        source="site",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = AccessRequest
        fields = (
            "id", "url", "display", "name", "status", "expected_date", "reason",
            "region", "region_id", "site", "site_id",
            "tags", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "status", "site")
        read_only_fields = ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        restrict_dcim_serializer_fields(self.fields, getattr(request, "user", None))

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance and not self.instance.can_guest_edit:
            raise serializers.ValidationError({"status": ACCESS_REQUEST_EDIT_LOCKED_MESSAGE})
        instance = self.instance or AccessRequest()
        for key, value in attrs.items():
            setattr(instance, key, value)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise_serializer_validation_error(exc)
        return attrs


class AccessRequestPersonSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_smartlock-api:accessrequestperson-detail")
    request = AccessRequestSerializer(nested=True, read_only=True)
    request_id = serializers.PrimaryKeyRelatedField(
        queryset=AccessRequest.objects.all(),
        source="request",
        write_only=True,
    )
    location = LocationSerializer(nested=True, read_only=True, required=False)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        source="location",
        write_only=True,
        required=False,
        allow_null=True,
    )
    upload_files = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = AccessRequestPerson
        fields = (
            "id", "url", "display", "request", "request_id",
            "identity_code", "full_name", "organization", "title", "phone",
            "location", "location_id", "description", "upload_files", "verify_status", "access_status",
            "tags", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "full_name", "identity_code", "verify_status", "access_status")
        read_only_fields = ("verify_status", "access_status")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        if request_user is not None:
            self.fields["request_id"].queryset = restrict_access_requests_for_user(
                self.fields["request_id"].queryset,
                request_user,
            )
            restrict_dcim_serializer_fields(self.fields, request_user)

    def validate(self, attrs):
        upload_files = attrs.pop("upload_files", serializers.empty)
        attrs = super().validate(attrs)
        self._upload_files_payload = None if upload_files is serializers.empty else upload_files
        instance = self.build_validation_instance(attrs)
        self.validate_request_scope(instance)
        self.validate_upload_requirement(attrs, upload_files)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise_serializer_validation_error(exc)
        return attrs

    def build_validation_instance(self, attrs):
        instance = self.instance or AccessRequestPerson()
        for key, value in attrs.items():
            setattr(instance, key, value)
        return instance

    def validate_request_scope(self, instance):
        access_request = getattr(instance, "request", None)
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        if request_user is not None and access_request and not user_can_access_request(request_user, access_request):
            raise serializers.ValidationError({"request": ACCESS_REQUEST_PERSON_SCOPE_DENIED_MESSAGE})
        if access_request and not access_request.can_guest_edit:
            raise serializers.ValidationError({"request": ACCESS_REQUEST_PERSON_EDIT_LOCKED_MESSAGE})

    def validate_upload_requirement(self, attrs, upload_files):
        # PATCH không đổi gì vẫn hợp lệ nếu object đã có file; create/update nội dung thì bắt buộc có file.
        enforce_attachment = not self.instance or bool(attrs) or upload_files is not serializers.empty
        if not enforce_attachment:
            return

        if upload_files is serializers.empty:
            if not self.has_existing_upload_files():
                raise serializers.ValidationError({"upload_files": ACCESS_REQUEST_PERSON_FILE_REQUIRED_MESSAGE})
            return

        if not upload_payload_has_valid_file(
            upload_files,
            instance=self.instance,
            model_name="accessrequestperson",
        ):
            raise serializers.ValidationError({"upload_files": ACCESS_REQUEST_PERSON_FILE_REQUIRED_MESSAGE})

    def has_existing_upload_files(self):
        return bool(
            self.instance
            and self.instance.pk
            and files_for_object(self.instance, model_name="accessrequestperson").exists()
        )

    def create(self, validated_data):
        instance = super().create(validated_data)
        self.sync_upload_files(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self.sync_upload_files(instance)
        return instance

    def sync_upload_files(self, instance):
        if self._upload_files_payload is not None:
            sync_uploaded_files(instance, self._upload_files_payload, model_name="accessrequestperson")
