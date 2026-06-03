from django.db import migrations


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
        comments=getattr(source, "comments", "") or "",
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
        comments=getattr(source, "comments", "") or "",
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
        comments=getattr(source, "comments", "") or "",
        parent=None,
        lft=1,
        rght=2,
        tree_id=next_tree_id,
        level=0,
    )


def migrate_catalog_uploads_to_dcim(apps, schema_editor):
    SLRegion = apps.get_model("netbox_smartlock", "SLRegion")
    SLSite = apps.get_model("netbox_smartlock", "SLSite")
    SLLocation = apps.get_model("netbox_smartlock", "SLLocation")
    Region = apps.get_model("dcim", "Region")
    Site = apps.get_model("dcim", "Site")
    Location = apps.get_model("dcim", "Location")
    UploadedFile = apps.get_model("upload_file_plugin", "UploadedFile")
    ContentType = apps.get_model("contenttypes", "ContentType")

    region_content_type, _ = ContentType.objects.get_or_create(app_label="dcim", model="region")
    site_content_type, _ = ContentType.objects.get_or_create(app_label="dcim", model="site")
    location_content_type, _ = ContentType.objects.get_or_create(app_label="dcim", model="location")

    region_map = {}
    for source in SLRegion.objects.all():
        region = _get_or_create_region(Region, source)
        region_map[source.pk] = region
        UploadedFile.objects.filter(model_name="slregion", object_id=source.pk).update(
            model_name="region",
            object_id=region.pk,
            content_type=region_content_type,
        )

    site_map = {}
    for source in SLSite.objects.select_related("region"):
        region = region_map.get(source.region_id) or _get_or_create_region(Region, source.region)
        site = _get_or_create_site(Site, source, region)
        site_map[source.pk] = site
        UploadedFile.objects.filter(model_name="slsite", object_id=source.pk).update(
            model_name="site",
            object_id=site.pk,
            content_type=site_content_type,
        )

    for source in SLLocation.objects.select_related("site__region"):
        site = site_map.get(source.site_id)
        if site is None:
            region = region_map.get(source.site.region_id) or _get_or_create_region(Region, source.site.region)
            site = _get_or_create_site(Site, source.site, region)

        location = _get_or_create_location(Location, source, site)
        UploadedFile.objects.filter(model_name="sllocation", object_id=source.pk).update(
            model_name="location",
            object_id=location.pk,
            content_type=location_content_type,
        )

    UploadedFile.objects.filter(model_name__in=("slregion", "slsite", "sllocation")).delete()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("dcim", "0001_initial"),
        ("upload_file_plugin", "0003_uploadedfile_file_no_upload_to"),
        ("netbox_smartlock", "0006_remove_smartlock_attachment"),
    ]

    operations = [
        migrations.RunPython(migrate_catalog_uploads_to_dcim, migrations.RunPython.noop),
        migrations.DeleteModel(name="SLLocation"),
        migrations.DeleteModel(name="SLSite"),
        migrations.DeleteModel(name="SLRegion"),
    ]
