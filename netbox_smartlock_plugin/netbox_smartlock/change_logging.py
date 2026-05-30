from django.contrib.contenttypes.models import ContentType
from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from core.choices import ObjectChangeActionChoices
from core.models.change_logging import ObjectChange


def annotate_creator(queryset, alias="created_by_name"):
    """Annotate người tạo từ ObjectChange của NetBox để tránh thêm field không cần thiết."""
    content_type = ContentType.objects.get_for_model(queryset.model)
    creator_subquery = (
        ObjectChange.objects.filter(
            changed_object_type=content_type,
            changed_object_id=OuterRef("pk"),
            action=ObjectChangeActionChoices.ACTION_CREATE,
        )
        .order_by("time")
        .values("user_name")[:1]
    )
    if any(field.name == "created_by" for field in queryset.model._meta.fields):
        return queryset.annotate(**{alias: Coalesce("created_by__username", Subquery(creator_subquery), Value(""))})
    return queryset.annotate(**{alias: Subquery(creator_subquery)})
