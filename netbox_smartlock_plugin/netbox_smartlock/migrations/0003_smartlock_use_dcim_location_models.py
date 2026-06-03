import django.db.models.deletion
from django.db import migrations, models


def _match_by_slug_or_name(queryset, source):
    slug = getattr(source, "slug", None)
    if slug:
        match = queryset.filter(slug=slug).first()
        if match:
            return match

    name = getattr(source, "name", None)
    if name:
        return queryset.filter(name=name).first()

    return None


def _get_or_create_region(Region, source):
    match = _match_by_slug_or_name(Region.objects.all(), source)
    if match:
        return match

    next_tree_id = (Region.objects.order_by("-tree_id").values_list("tree_id", flat=True).first() or 0) + 1
    return Region.objects.create(
        name=source.name,
        slug=source.slug,
        description="",
        comments="",
        parent=None,
        lft=1,
        rght=2,
        tree_id=next_tree_id,
        level=0,
    )


def _get_or_create_site(Site, source, region):
    match = _match_by_slug_or_name(Site.objects.filter(region=region), source)
    if match:
        return match

    match = _match_by_slug_or_name(Site.objects.all(), source)
    if match:
        return match

    return Site.objects.create(
        name=source.name,
        slug=source.slug,
        status="active",
        region=region,
        facility=getattr(source, "code", "") or "",
        description="",
        comments="",
        physical_address="",
        shipping_address="",
    )


def _get_or_create_location(Location, source, site):
    match = _match_by_slug_or_name(Location.objects.filter(site=site), source)
    if match:
        return match

    match = _match_by_slug_or_name(Location.objects.all(), source)
    if match:
        return match

    next_tree_id = (Location.objects.order_by("-tree_id").values_list("tree_id", flat=True).first() or 0) + 1
    return Location.objects.create(
        name=source.name,
        slug=source.slug,
        status="active",
        site=site,
        facility=getattr(source, "code", "") or "",
        description="",
        comments="",
        parent=None,
        lft=1,
        rght=2,
        tree_id=next_tree_id,
        level=0,
    )


def migrate_smartlock_location_refs(apps, schema_editor):
    SmartLock = apps.get_model("netbox_smartlock", "SmartLock")
    Region = apps.get_model("dcim", "Region")
    Site = apps.get_model("dcim", "Site")
    Location = apps.get_model("dcim", "Location")

    for lock in SmartLock.objects.select_related("region", "site", "location"):
        dcim_region = _get_or_create_region(Region, lock.region)
        dcim_site = _get_or_create_site(Site, lock.site, dcim_region)
        dcim_location = _get_or_create_location(Location, lock.location, dcim_site)

        lock.nb_region_id = dcim_region.pk
        lock.nb_site_id = dcim_site.pk
        lock.nb_location_id = dcim_location.pk
        lock.save(update_fields=("nb_region", "nb_site", "nb_location"))


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("dcim", "0001_initial"),
        ("netbox_smartlock", "0002_smartlock_rack_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="smartlock",
            name="nb_region",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="dcim.region",
                verbose_name="Region",
            ),
        ),
        migrations.AddField(
            model_name="smartlock",
            name="nb_site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="dcim.site",
                verbose_name="Site",
            ),
        ),
        migrations.AddField(
            model_name="smartlock",
            name="nb_location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="dcim.location",
                verbose_name="Location",
            ),
        ),
        migrations.RunPython(migrate_smartlock_location_refs, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="smartlock",
            name="region",
        ),
        migrations.RemoveField(
            model_name="smartlock",
            name="site",
        ),
        migrations.RemoveField(
            model_name="smartlock",
            name="location",
        ),
        migrations.RenameField(
            model_name="smartlock",
            old_name="nb_region",
            new_name="region",
        ),
        migrations.RenameField(
            model_name="smartlock",
            old_name="nb_site",
            new_name="site",
        ),
        migrations.RenameField(
            model_name="smartlock",
            old_name="nb_location",
            new_name="location",
        ),
        migrations.AlterField(
            model_name="smartlock",
            name="region",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlocks",
                to="dcim.region",
                verbose_name="Region",
            ),
        ),
        migrations.AlterField(
            model_name="smartlock",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlocks",
                to="dcim.site",
                verbose_name="Site",
            ),
        ),
        migrations.AlterField(
            model_name="smartlock",
            name="location",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="smartlocks",
                to="dcim.location",
                verbose_name="Location",
            ),
        ),
    ]
