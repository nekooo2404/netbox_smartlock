from datetime import timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone

from dcim.models import Location, Rack, Region, Site
from netbox.filtersets import NetBoxModelFilterSet

from .mapping import WARRANTY_STATE_EXPIRED, WARRANTY_STATE_EXPIRING, WARRANTY_STATE_MISSING, WARRANTY_STATE_VALID
from .models import AccessRequest, AccessRequestPerson, AssetGroup, SmartLock
from .ui import (
    ACCESS_REQUEST_PERSON_ACCESS_LABELS,
    ACCESS_REQUEST_PERSON_VERIFY_LABELS,
    ACCESS_REQUEST_STATUS_LABELS,
    RACK_FACE_LABELS,
    SMARTLOCK_STATUS_LABELS,
    WARRANTY_STATE_LABELS,
    choices_with_labels,
)


class AssetGroupFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = AssetGroup
        fields = ("id", "name", "slug", "code", "status")

    def search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(code__icontains=value) | Q(slug__icontains=value))


class SmartLockFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(
        choices=choices_with_labels(SmartLock.STATUS_CHOICES, SMARTLOCK_STATUS_LABELS),
        label="Trạng thái",
    )
    asset_group_id = django_filters.ModelMultipleChoiceFilter(
        queryset=AssetGroup.objects.all(),
        label="Nhóm tài sản",
    )
    region_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Region.objects.all(),
        label="Khu vực",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Địa điểm",
    )
    location_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Vị trí",
    )
    rack_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        label="Tủ rack",
    )
    rack_face = django_filters.MultipleChoiceFilter(
        choices=choices_with_labels(SmartLock.RACK_FACE_CHOICES, RACK_FACE_LABELS),
        label="Mặt tủ rack",
    )
    device_model = django_filters.CharFilter(
        field_name="model",
        lookup_expr="icontains",
        label="Model",
    )
    warranty_state = django_filters.MultipleChoiceFilter(
        choices=(
            (WARRANTY_STATE_VALID, WARRANTY_STATE_LABELS[WARRANTY_STATE_VALID]),
            (WARRANTY_STATE_EXPIRING, WARRANTY_STATE_LABELS[WARRANTY_STATE_EXPIRING]),
            (WARRANTY_STATE_EXPIRED, WARRANTY_STATE_LABELS[WARRANTY_STATE_EXPIRED]),
            (WARRANTY_STATE_MISSING, WARRANTY_STATE_LABELS[WARRANTY_STATE_MISSING]),
        ),
        method="filter_warranty_state",
        label="Trạng thái bảo hành",
    )

    class Meta:
        model = SmartLock
        fields = (
            "id", "name", "code", "status",
            "asset_group_id", "device_type", "manufacturer", "serial", "device_model",
            "region_id", "site_id", "location_id", "rack_id", "rack_face",
            "warranty_state",
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(code__icontains=value)
            | Q(device_type__icontains=value)
            | Q(manufacturer__icontains=value)
            | Q(serial__icontains=value)
            | Q(model__icontains=value)
            | Q(description__icontains=value)
            | Q(asset_group__name__icontains=value)
            | Q(site__name__icontains=value)
            | Q(location__name__icontains=value)
            | Q(rack__name__icontains=value)
        )

    def filter_warranty_state(self, queryset, name, value):
        if not value:
            return queryset

        today = timezone.localdate()
        warning_date = today + timedelta(days=30)
        predicate = Q()

        if WARRANTY_STATE_VALID in value:
            predicate |= Q(warranty_expiration_date__gt=warning_date)
        if WARRANTY_STATE_EXPIRING in value:
            predicate |= Q(warranty_expiration_date__gte=today, warranty_expiration_date__lte=warning_date)
        if WARRANTY_STATE_EXPIRED in value:
            predicate |= Q(warranty_expiration_date__lt=today)
        if WARRANTY_STATE_MISSING in value:
            predicate |= Q(warranty_expiration_date__isnull=True)

        return queryset.filter(predicate)


class AccessRequestFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(
        choices=choices_with_labels(AccessRequest.STATUS_CHOICES, ACCESS_REQUEST_STATUS_LABELS),
        label="Trạng thái",
    )
    region_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Region.objects.all(),
        label="Khu vực",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Địa điểm",
    )

    class Meta:
        model = AccessRequest
        fields = ("id", "name", "status", "region_id", "site_id", "expected_date")

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(status__icontains=value)
            | Q(reason__icontains=value)
            | Q(site__name__icontains=value)
            | Q(region__name__icontains=value)
        )


class AccessRequestPersonFilterSet(NetBoxModelFilterSet):
    request_id = django_filters.ModelMultipleChoiceFilter(
        queryset=AccessRequest.objects.all(),
        label="Phiếu yêu cầu vào ra",
    )
    verify_status = django_filters.MultipleChoiceFilter(
        choices=choices_with_labels(AccessRequestPerson.VERIFY_STATUS_CHOICES, ACCESS_REQUEST_PERSON_VERIFY_LABELS),
        label="Trạng thái xác minh",
    )
    access_status = django_filters.MultipleChoiceFilter(
        choices=choices_with_labels(AccessRequestPerson.ACCESS_STATUS_CHOICES, ACCESS_REQUEST_PERSON_ACCESS_LABELS),
        label="Trạng thái vào ra",
    )
    location_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Vị trí",
    )

    class Meta:
        model = AccessRequestPerson
        fields = (
            "id", "request_id", "identity_code", "full_name", "organization",
            "verify_status", "access_status", "location_id",
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(identity_code__icontains=value)
            | Q(full_name__icontains=value)
            | Q(organization__icontains=value)
            | Q(title__icontains=value)
            | Q(phone__icontains=value)
            | Q(request__name__icontains=value)
        )
