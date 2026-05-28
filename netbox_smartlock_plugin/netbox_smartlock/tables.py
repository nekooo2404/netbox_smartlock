import django_tables2 as tables
from django.utils.html import format_html

from netbox.tables import NetBoxTable, columns

from .mapping import get_warranty_state
from .models import AccessRequest, AccessRequestPerson, AssetGroup, SmartLock
from .permissions import is_access_request_admin
from .upload_files import file_names_for_object


class GuestWorkflowActionsColumn(columns.ActionsColumn):
    def render(self, record, table, **kwargs):
        original_actions = self.actions
        try:
            actions = dict(original_actions)
            request = getattr(table, "context", {}).get("request") if getattr(table, "context", None) else None
            user = getattr(request, "user", None)
            if is_access_request_admin(user):
                actions.pop("edit", None)
                actions.pop("delete", None)
            elif not getattr(record, "can_guest_edit", True):
                actions.pop("edit", None)
                if not getattr(record, "can_guest_delete", True):
                    actions.pop("delete", None)
            elif not getattr(record, "can_guest_delete", True):
                actions.pop("delete", None)
            self.actions = actions
            return super().render(record, table, **kwargs)
        finally:
            self.actions = original_actions


class AssetGroupTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    uploaded_file_count = tables.Column(verbose_name="File Count", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:assetgroup_list")

    def render_uploaded_file_count(self, record):
        return getattr(record, "uploaded_file_count", 0)

    class Meta(NetBoxTable.Meta):
        model = AssetGroup
        fields = (
            "pk", "id", "name", "slug", "code", "status",
            "description", "uploaded_file_count", "tags",
            "created", "last_updated", "actions",
        )
        default_columns = ("name", "code", "status", "description", "uploaded_file_count")


class SmartLockTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    asset_group = tables.Column(linkify=True)
    created_by_name = tables.Column(verbose_name="Created By", order_by=("created_by_name",))
    region = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    rack = tables.Column(linkify=True)
    rack_face = tables.Column(verbose_name="Rack Face")
    warranty_expiration_date = tables.DateColumn()
    warranty_state = tables.Column(verbose_name="Warranty", accessor="warranty_expiration_date", orderable=False)
    uploaded_file_count = tables.Column(verbose_name="File Count", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:smartlock_list")

    def render_uploaded_file_count(self, record):
        return getattr(record, "uploaded_file_count", 0)

    def render_warranty_state(self, value, record):
        state = get_warranty_state(record.warranty_expiration_date)
        label_map = {
            "valid": ("success", "Valid"),
            "expiring": ("warning", "Expiring soon"),
            "expired": ("danger", "Expired"),
            "missing": ("secondary", "Not set"),
        }
        color, label = label_map[state]
        return format_html('<span class="badge text-bg-{}">{}</span>', color, label)

    class Meta(NetBoxTable.Meta):
        model = SmartLock
        fields = (
            "pk", "id", "name", "code", "status", "asset_group",
            "device_type", "manufacturer", "model", "serial", "created_by_name",
            "region", "site", "location", "rack", "rack_face",
            "setup_date", "bought_date", "warranty_period", "warranty_expiration_date", "warranty_state",
            "uploaded_file_count", "tags", "created", "last_updated", "actions",
        )
        default_columns = (
            "name", "code", "status", "asset_group", "manufacturer", "device_type",
            "site", "location", "rack", "warranty_state", "uploaded_file_count",
        )


class AccessRequestTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    region = tables.Column(linkify=True)
    site = tables.Column(linkify=True)
    created_by_name = tables.Column(verbose_name="Created By", order_by=("created_by_name",))
    person_count = tables.Column(verbose_name="Persons", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:accessrequest_list")
    actions = GuestWorkflowActionsColumn()

    def render_person_count(self, record):
        return getattr(record, "person_count", 0)

    class Meta(NetBoxTable.Meta):
        model = AccessRequest
        fields = (
            "pk", "id", "name", "status", "reason", "expected_date",
            "region", "site", "created_by_name", "person_count", "tags",
            "created", "last_updated", "actions",
        )
        default_columns = (
            "name", "status", "reason", "expected_date", "region", "site",
            "created_by_name", "created", "last_updated", "actions",
        )


class AccessRequestPersonTable(NetBoxTable):
    full_name = tables.Column(linkify=True)
    request = tables.Column(linkify=True)
    verify_status = columns.ChoiceFieldColumn()
    access_status = columns.ChoiceFieldColumn()
    location = tables.Column(linkify=True)
    uploaded_file_count = tables.Column(verbose_name="Files", orderable=False)
    uploaded_file_names = tables.Column(verbose_name="Attachment Files", orderable=False, empty_values=())
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:accessrequestperson_list")
    actions = GuestWorkflowActionsColumn()

    def render_uploaded_file_count(self, record):
        return getattr(record, "uploaded_file_count", 0)

    def render_uploaded_file_names(self, record):
        names = file_names_for_object(record, model_name="accessrequestperson")
        return ", ".join(names) if names else "-"

    class Meta(NetBoxTable.Meta):
        model = AccessRequestPerson
        fields = (
            "pk", "id", "request", "identity_code", "full_name", "organization",
            "title", "phone", "location", "description", "uploaded_file_count", "uploaded_file_names",
            "verify_status", "access_status", "tags", "created", "last_updated", "actions",
        )
        default_columns = (
            "full_name", "identity_code", "organization", "title", "verify_status", "access_status",
            "created", "last_updated", "uploaded_file_names", "actions",
        )
