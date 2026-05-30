import django_tables2 as tables
from django.utils.html import format_html

from netbox.tables import NetBoxTable, columns

from .mapping import get_warranty_state
from .models import AccessRequest, AccessRequestPerson, AssetGroup, SmartLock
from .permissions import is_access_request_admin
from .ui import (
    ACCESS_REQUEST_PERSON_ACCESS_LABELS,
    ACCESS_REQUEST_PERSON_VERIFY_LABELS,
    ACCESS_REQUEST_STATUS_LABELS,
    ASSET_GROUP_STATUS_LABELS,
    RACK_FACE_LABELS,
    SMARTLOCK_STATUS_LABELS,
    WARRANTY_STATE_LABELS,
    label_for,
)
from .upload_files import file_names_for_object


class GuestWorkflowActionsColumn(columns.ActionsColumn):
    """Ẩn action CRUD theo workflow Guest/Admin nhưng vẫn để backend kiểm quyền thật sự."""

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
    name = tables.Column(linkify=True, verbose_name="Tên")
    slug = tables.Column(verbose_name="Slug")
    code = tables.Column(verbose_name="Mã")
    status = tables.Column(verbose_name="Trạng thái")
    description = tables.Column(verbose_name="Mô tả")
    uploaded_file_count = tables.Column(verbose_name="Số file", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:assetgroup_list")

    def render_status(self, value):
        return label_for(ASSET_GROUP_STATUS_LABELS, value)

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
    name = tables.Column(linkify=True, verbose_name="Tên")
    code = tables.Column(verbose_name="Mã")
    status = tables.Column(verbose_name="Trạng thái")
    asset_group = tables.Column(linkify=True, verbose_name="Nhóm tài sản")
    device_type = tables.Column(verbose_name="Loại thiết bị")
    manufacturer = tables.Column(verbose_name="Nhà sản xuất")
    model = tables.Column(verbose_name="Model")
    serial = tables.Column(verbose_name="Serial")
    created_by_name = tables.Column(verbose_name="Người tạo", order_by=("created_by_name",))
    region = tables.Column(linkify=True, verbose_name="Khu vực")
    site = tables.Column(linkify=True, verbose_name="Địa điểm")
    location = tables.Column(linkify=True, verbose_name="Vị trí")
    rack = tables.Column(linkify=True, verbose_name="Tủ rack")
    rack_face = tables.Column(verbose_name="Mặt tủ rack")
    setup_date = tables.DateColumn(verbose_name="Ngày lắp đặt")
    bought_date = tables.DateColumn(verbose_name="Ngày mua")
    warranty_period = tables.Column(verbose_name="Thời hạn bảo hành")
    warranty_expiration_date = tables.DateColumn(verbose_name="Ngày hết hạn bảo hành")
    warranty_state = tables.Column(verbose_name="Bảo hành", accessor="warranty_expiration_date", orderable=False)
    uploaded_file_count = tables.Column(verbose_name="Số file", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:smartlock_list")

    def render_status(self, value):
        return label_for(SMARTLOCK_STATUS_LABELS, value)

    def render_rack_face(self, value):
        return label_for(RACK_FACE_LABELS, value)

    def render_uploaded_file_count(self, record):
        return getattr(record, "uploaded_file_count", 0)

    def render_warranty_state(self, value, record):
        state = get_warranty_state(record.warranty_expiration_date)
        label_map = {
            "valid": ("success", WARRANTY_STATE_LABELS["valid"]),
            "expiring": ("warning", WARRANTY_STATE_LABELS["expiring"]),
            "expired": ("danger", WARRANTY_STATE_LABELS["expired"]),
            "missing": ("secondary", WARRANTY_STATE_LABELS["missing"]),
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
    name = tables.Column(linkify=True, verbose_name="Tên phiếu")
    status = tables.Column(verbose_name="Trạng thái")
    reason = tables.Column(verbose_name="Lý do")
    expected_date = tables.DateColumn(verbose_name="Ngày dự kiến")
    region = tables.Column(linkify=True, verbose_name="Khu vực")
    site = tables.Column(linkify=True, verbose_name="Địa điểm")
    created_by_name = tables.Column(verbose_name="Người tạo", order_by=("created_by_name",))
    person_count = tables.Column(verbose_name="Số đối tượng", orderable=False)
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:accessrequest_list")
    actions = GuestWorkflowActionsColumn()

    def render_status(self, value):
        return label_for(ACCESS_REQUEST_STATUS_LABELS, value)

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
    full_name = tables.Column(linkify=True, verbose_name="Họ tên")
    request = tables.Column(linkify=True, verbose_name="Phiếu yêu cầu")
    identity_code = tables.Column(verbose_name="CCCD/CMND")
    organization = tables.Column(verbose_name="Đơn vị")
    title = tables.Column(verbose_name="Chức danh")
    phone = tables.Column(verbose_name="Số điện thoại")
    verify_status = tables.Column(verbose_name="Xác minh")
    access_status = tables.Column(verbose_name="Trạng thái vào ra")
    location = tables.Column(linkify=True, verbose_name="Vị trí")
    description = tables.Column(verbose_name="Mô tả")
    uploaded_file_count = tables.Column(verbose_name="Số file", orderable=False)
    uploaded_file_names = tables.Column(verbose_name="File đính kèm", orderable=False, empty_values=())
    tags = columns.TagColumn(url_name="plugins:netbox_smartlock:accessrequestperson_list")
    actions = GuestWorkflowActionsColumn()

    def render_verify_status(self, value):
        return label_for(ACCESS_REQUEST_PERSON_VERIFY_LABELS, value)

    def render_access_status(self, value):
        return label_for(ACCESS_REQUEST_PERSON_ACCESS_LABELS, value)

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
