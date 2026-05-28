from collections import defaultdict
import json

from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from upload_file_plugin.integration import get_uploaded_files
from upload_file_plugin.models import UploadedFile
from upload_file_plugin.services import is_allowed_image, is_allowed_size, resolve_temp_upload_path


def files_for_object(instance, model_name=None):
    return get_uploaded_files(instance, model_name=model_name or instance._meta.model_name)


def file_names_for_object(instance, model_name=None):
    return [
        file_obj.file_name or file_obj.file.name
        for file_obj in files_for_object(instance, model_name=model_name)
    ]


def file_count_for_object(instance, model_name=None):
    return files_for_object(instance, model_name=model_name).count()


def upload_payload_has_valid_file(upload_files, instance=None, model_name=None):
    if isinstance(upload_files, str):
        try:
            payload = json.loads(upload_files or "[]")
        except json.JSONDecodeError:
            return False
    else:
        payload = upload_files or []

    existing_file_ids = set()
    if instance and instance.pk:
        existing_file_ids = set(
            files_for_object(instance, model_name=model_name).values_list("pk", flat=True)
        )

    for item in payload:
        if not isinstance(item, dict):
            continue

        try:
            file_id = int(item.get("id") or 0)
        except (TypeError, ValueError):
            file_id = 0
        if file_id and file_id in existing_file_ids:
            return True

        file_name = item.get("file_name") or item.get("name")
        temp_path = resolve_temp_upload_path(item.get("path") or "")
        if not (file_name and temp_path and is_allowed_image(file_name)):
            continue
        try:
            file_size = temp_path.stat().st_size
        except OSError:
            continue
        if is_allowed_size(file_size):
            return True

    return False


def annotate_file_count(queryset, model_name, alias="uploaded_file_count"):
    file_count = (
        UploadedFile.objects.filter(model_name=model_name, object_id=OuterRef("pk"))
        .values("object_id")
        .annotate(count=Count("pk"))
        .values("count")
    )
    return queryset.annotate(
        **{
            alias: Coalesce(
                Subquery(file_count, output_field=IntegerField()),
                Value(0),
            )
        }
    )


def file_names_by_object_ids(object_ids, model_name):
    names_by_id = defaultdict(list)
    if not object_ids:
        return names_by_id

    files = UploadedFile.objects.filter(
        model_name=model_name,
        object_id__in=object_ids,
    ).order_by("created_at", "pk")
    for file_obj in files:
        names_by_id[file_obj.object_id].append(file_obj.file_name or file_obj.file.name)

    return names_by_id
