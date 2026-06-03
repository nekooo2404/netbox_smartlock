from django.urls import reverse


def asset_group_device_filter_url(asset_group):
    return f"{reverse('plugins:netbox_smartlock:asset_list')}?asset_group_id={asset_group.pk}"


def assets_for_asset_group(asset_group, user=None):
    from .models import Asset

    queryset = (
        Asset.objects.select_related(
            "asset_group",
            "device",
            "device__device_type__manufacturer",
            "device__site",
            "device__location",
            "device__rack",
        )
        .filter(asset_group=asset_group)
    )

    if user is not None and hasattr(queryset, "restrict"):
        queryset = queryset.restrict(user, "view")

    return queryset


devices_for_asset_group = assets_for_asset_group
