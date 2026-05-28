from datetime import timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone

from dcim.models import Location, Rack, Region, Site
from netbox.filtersets import NetBoxModelFilterSet

from .mapping import WARRANTY_STATE_EXPIRED, WARRANTY_STATE_EXPIRING, WARRANTY_STATE_MISSING, WARRANTY_STATE_VALID
from .models import AccessRequest, AccessRequestPerson, AssetGroup, SmartLock


class AssetGroupFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = AssetGroup
        fields = ("id", "name", "slug", "code", "status")

    def search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(code__icontains=value) | Q(slug__icontains=value))


class SmartLockFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(
        choices=SmartLock.STATUS_CHOICES,
        label="Status",
    )
    asset_group_id = django_filters.ModelMultipleChoiceFilter(
        queryset=AssetGroup.objects.all(),
        label="Asset Group",
    )
    region_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Region.objects.all(),
        label="Region",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site",
    )
    location_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Location",
    )
    rack_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        label="Rack",
    )
    rack_face = django_filters.MultipleChoiceFilter(
        choices=SmartLock.RACK_FACE_CHOICES,
        label="Rack Face",
    )
    device_model = django_filters.CharFilter(
        field_name="model",
        lookup_expr="icontains",
        label="Model",
    )
    warranty_state = django_filters.MultipleChoiceFilter(
        choices=(
            (WARRANTY_STATE_VALID, "Valid"),
            (WARRANTY_STATE_EXPIRING, "Expiring soon"),
            (WARRANTY_STATE_EXPIRED, "Expired"),
            (WARRANTY_STATE_MISSING, "Not set"),
        ),
        method="filter_warranty_state",
        label="Warranty State",
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
        choices=AccessRequest.STATUS_CHOICES,
        label="Status",
    )
    region_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Region.objects.all(),
        label="Region",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site",
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
        label="Access Request",
    )
    verify_status = django_filters.MultipleChoiceFilter(
        choices=AccessRequestPerson.VERIFY_STATUS_CHOICES,
        label="Verification Status",
    )
    access_status = django_filters.MultipleChoiceFilter(
        choices=AccessRequestPerson.ACCESS_STATUS_CHOICES,
        label="Access Status",
    )
    location_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Location",
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
