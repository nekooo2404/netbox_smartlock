import django.db.models.deletion
from django.db import migrations, models


def backfill_asset_dicm_fields(apps, schema_editor):
    Asset = apps.get_model("netbox_smartlock", "Asset")

    queryset = Asset.objects.select_related(
        "device",
        "device__site",
        "device__location",
        "device__device_type__manufacturer",
    )
    for asset in queryset.iterator():
        update_fields = []
        device = asset.device
        if device is None:
            continue

        if not asset.site_id and getattr(device, "site_id", None):
            asset.site_id = device.site_id
            update_fields.append("site")
        if not asset.location_id and getattr(device, "location_id", None):
            asset.location_id = device.location_id
            update_fields.append("location")
        site = getattr(device, "site", None)
        if not asset.region_id and getattr(site, "region_id", None):
            asset.region_id = site.region_id
            update_fields.append("region")
        if not asset.device_type and getattr(device, "device_type", None):
            asset.device_type = str(device.device_type)[:100]
            update_fields.append("device_type")
        manufacturer = getattr(getattr(device, "device_type", None), "manufacturer", None)
        if not asset.manufacturer and manufacturer:
            asset.manufacturer = str(manufacturer)[:100]
            update_fields.append("manufacturer")
        if not asset.serial and getattr(device, "serial", ""):
            asset.serial = str(device.serial)[:100]
            update_fields.append("serial")

        if update_fields:
            asset.save(update_fields=tuple(update_fields))


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0001_initial"),
        ("netbox_smartlock", "0016_asset_model"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asset",
            name="device",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlock_asset",
                to="dcim.device",
                verbose_name="DCIM Device",
            ),
        ),
        migrations.AddField(
            model_name="asset",
            name="device_type",
            field=models.CharField(default="", max_length=100, verbose_name="Device Type"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="asset",
            name="model",
            field=models.CharField(blank=True, max_length=100, verbose_name="Model"),
        ),
        migrations.AddField(
            model_name="asset",
            name="serial",
            field=models.CharField(blank=True, max_length=100, verbose_name="Serial"),
        ),
        migrations.AddField(
            model_name="asset",
            name="manufacturer",
            field=models.CharField(blank=True, max_length=100, verbose_name="Manufacturer"),
        ),
        migrations.AddField(
            model_name="asset",
            name="region",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlock_assets",
                to="dcim.region",
                verbose_name="Region",
            ),
        ),
        migrations.AddField(
            model_name="asset",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlock_assets",
                to="dcim.site",
                verbose_name="Site",
            ),
        ),
        migrations.AddField(
            model_name="asset",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlock_assets",
                to="dcim.location",
                verbose_name="Location",
            ),
        ),
        migrations.RunPython(backfill_asset_dicm_fields, migrations.RunPython.noop),
    ]
