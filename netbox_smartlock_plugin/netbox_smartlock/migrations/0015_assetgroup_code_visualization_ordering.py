import django.core.validators

from django.db import migrations, models
from django.db.models import Q


def build_unique_code(AssetGroup, asset_group):
    source = asset_group.code or asset_group.slug or asset_group.name or f"asset-group-{asset_group.pk}"
    base = str(source).strip()[:50] or f"asset-group-{asset_group.pk}"
    code = base
    suffix = 1

    while AssetGroup.objects.exclude(pk=asset_group.pk).filter(code=code).exists():
        suffix_text = f"-{suffix}"
        code = f"{base[:50 - len(suffix_text)]}{suffix_text}"
        suffix += 1

    return code


def backfill_assetgroup_code(apps, schema_editor):
    AssetGroup = apps.get_model("netbox_smartlock", "AssetGroup")
    for asset_group in AssetGroup.objects.filter(Q(code__isnull=True) | Q(code="")):
        asset_group.code = build_unique_code(AssetGroup, asset_group)
        asset_group.save(update_fields=("code",))


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_smartlock", "0014_share_asset_group_with_dcim_device"),
    ]

    operations = [
        migrations.RunPython(backfill_assetgroup_code, migrations.RunPython.noop),
        migrations.AddField(
            model_name="assetgroup",
            name="exclude_from_visualization",
            field=models.BooleanField(default=False, verbose_name="Exclude from Visualization"),
        ),
        migrations.AlterField(
            model_name="assetgroup",
            name="code",
            field=models.CharField(max_length=50, unique=True, verbose_name="Code"),
        ),
        migrations.AlterField(
            model_name="assetgroup",
            name="description",
            field=models.TextField(
                blank=True,
                validators=[django.core.validators.MaxLengthValidator(500)],
                verbose_name="Description",
            ),
        ),
        migrations.AlterModelOptions(
            name="assetgroup",
            options={
                "ordering": ("-last_updated", "name"),
                "verbose_name": "Asset Group",
                "verbose_name_plural": "Asset Groups",
            },
        ),
    ]
