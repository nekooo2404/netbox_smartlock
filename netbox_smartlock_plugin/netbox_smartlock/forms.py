from django import forms

from dcim.models import Location, Rack, Region, Site
from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm, NetBoxModelImportForm
from utilities.forms.fields import (
    CSVChoiceField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    SlugField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet

from upload_file_plugin.integration import UploadFileFormMixin

from .contracts import SMARTLOCK_IMPORT_MODEL_FIELDS
from .mapping import (
    WARRANTY_STATE_CHOICES,
    normalize_text,
)
from .messages import (
    ACCESS_REQUEST_PERSON_EDIT_LOCKED_MESSAGE,
    ACCESS_REQUEST_PERSON_FILE_REQUIRED_MESSAGE,
    ACCESS_REQUEST_PERSON_IMPORT_LOCKED_MESSAGE,
    ACCESS_REQUEST_PERSON_IMPORT_SCOPE_DENIED_MESSAGE,
    ACCESS_REQUEST_PERSON_SCOPED_REQUEST_UNAVAILABLE_MESSAGE,
    ACCESS_REQUEST_PERSON_SCOPE_DENIED_MESSAGE,
    ACCESS_REQUEST_REQUIRED_MESSAGE,
)
from .models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock
from .permissions import restrict_access_request_persons_for_user, restrict_access_requests_for_user, user_can_access_request
from .services import normalize_smartlock_form_data, normalize_smartlock_import_data
from .ui import (
    ACCESS_REQUEST_PERSON_ACCESS_LABELS,
    ACCESS_REQUEST_PERSON_VERIFY_LABELS,
    ACCESS_REQUEST_STATUS_LABELS,
    ASSET_GROUP_STATUS_LABELS,
    ASSET_STATUS_LABELS,
    RACK_FACE_LABELS,
    SMARTLOCK_STATUS_LABELS,
    WARRANTY_STATE_LABELS,
    choices_with_labels,
)
from .upload_files import upload_payload_has_valid_file


DCIM_SCOPE_FIELD_NAMES = (
    "region", "region_id", "site", "site_id",
    "location", "location_id", "rack", "rack_id",
)
IMPORT_COMMON_FIELD_LABELS = {
    "id": "ID",
    "tags": "Tags",
    "changelog_message": "Thông điệp nhật ký thay đổi",
    "background_job": "Chạy nền",
    "data": "Dữ liệu",
    "format": "Định dạng",
    "csv_delimiter": "Ký tự phân tách CSV",
    "upload_file": "File tải lên",
    "data_source": "Nguồn dữ liệu",
    "data_file": "File dữ liệu",
}
IMPORT_COMMON_FIELD_HELP_TEXTS = {
    "id": "ID số của bản ghi hiện có cần cập nhật; để trống khi tạo mới.",
    "tags": 'Slug tag, phân tách bằng dấu phẩy và đặt trong dấu nháy kép, ví dụ "tag1,tag2,tag3".',
    "changelog_message": "",
    "background_job": "Xử lý import bằng background job.",
}
BULK_COMMON_FIELD_LABELS = {
    "changelog_message": "Thông điệp nhật ký thay đổi",
    "background_job": "Chạy nền",
    "add_tags": "Thêm tag",
    "remove_tags": "Xóa tag",
    "find": "Tìm",
    "replace": "Thay bằng",
    "use_regex": "Dùng regex",
}
BULK_COMMON_FIELD_HELP_TEXTS = {
    "changelog_message": "",
    "background_job": "Xử lý thao tác bằng background job.",
}


def restrict_dcim_scope_fields(form, user, action="view"):
    """Giới hạn lựa chọn DCIM theo object permission của NetBox."""
    if user is None:
        return

    for field_name in DCIM_SCOPE_FIELD_NAMES:
        field = form.fields.get(field_name)
        queryset = getattr(field, "queryset", None)
        if queryset is not None and hasattr(queryset, "restrict"):
            field.queryset = queryset.restrict(user, action)


def restrict_asset_group_field(form, user, action="view"):
    """Chỉ cho chọn nhóm tài sản đang hoạt động và nằm trong scope quyền của user."""
    field = form.fields.get("asset_group")
    queryset = getattr(field, "queryset", None)
    if queryset is None:
        return

    queryset = queryset.filter(status=AssetGroup.STATUS_ACTIVE)
    if user is not None and hasattr(queryset, "restrict"):
        queryset = queryset.restrict(user, action)
    field.queryset = queryset


def object_in_user_scope(obj, user, action="view"):
    """Kiểm tra object đã submit có còn nằm trong queryset restrict của NetBox hay không."""
    if obj is None or user is None:
        return True

    queryset = obj.__class__.objects.filter(pk=obj.pk)
    if hasattr(queryset, "restrict"):
        queryset = queryset.restrict(user, action)
    return queryset.exists()


def apply_field_labels_and_help_texts(form, labels, help_texts=None):
    help_texts = help_texts or {}
    for field_name, label in labels.items():
        field = form.fields.get(field_name)
        if field is None:
            continue
        field.label = label
        if field_name in help_texts:
            field.help_text = help_texts[field_name]


def translate_import_common_fields(form):
    """Việt hóa các field chung do NetBox thêm vào form import."""
    apply_field_labels_and_help_texts(form, IMPORT_COMMON_FIELD_LABELS, IMPORT_COMMON_FIELD_HELP_TEXTS)


def translate_bulk_common_fields(form):
    """Việt hóa các field chung do NetBox thêm vào form bulk action."""
    apply_field_labels_and_help_texts(form, BULK_COMMON_FIELD_LABELS, BULK_COMMON_FIELD_HELP_TEXTS)


def scope_location_field_to_access_request(form, access_request):
    if not access_request or not access_request.site_id:
        return

    location_field = form.fields["location"]
    location_field.queryset = location_field.queryset.filter(site=access_request.site)
    if hasattr(location_field.widget, "add_query_param"):
        location_field.widget.add_query_param("site_id", str(access_request.site_id))


def enable_dynamic_location_scope(form):
    location_widget = form.fields["location"].widget
    location_widget.attrs["data-smartlock-request-field"] = "id_request"
    location_widget.attrs["data-smartlock-location-scope"] = "true"


def add_required_upload_error(form, upload_files, *, instance=None):
    has_valid_file = upload_payload_has_valid_file(
        upload_files,
        instance=instance,
        model_name=form.upload_file_model_name,
    )
    if not has_valid_file:
        form.add_error(form.upload_file_field_name, ACCESS_REQUEST_PERSON_FILE_REQUIRED_MESSAGE)


ASSETGROUP_VISUALIZATION_HELP_TEXT = (
    "Checked: tất cả tài sản thuộc nhóm tài sản này sẽ được thêm vào visualization. "
    "Unchecked: các tài sản thuộc nhóm tài sản này sẽ không được thêm vào visualization."
)


class AssetGroupForm(UploadFileFormMixin, NetBoxModelForm):
    upload_file_model_name = "assetgroup"
    slug = SlugField()

    fieldsets = (
        FieldSet("name", "slug", "code", "status", "exclude_from_visualization", name="Thông tin chính"),
        FieldSet("description", "comments", name="Mô tả"),
        FieldSet("upload_files", "tags", name="Dữ liệu bổ sung"),
    )

    class Meta:
        model = AssetGroup
        fields = ("name", "slug", "code", "status", "exclude_from_visualization", "description", "comments", "tags")
        labels = {
            "name": "Tên",
            "code": "Mã",
            "status": "Trạng thái",
            "exclude_from_visualization": "Exclude from Visualization",
            "description": "Mô tả",
            "comments": "Ghi chú",
        }
        help_texts = {
            "code": "Mã nhóm dùng cho nhập/xuất dữ liệu và đối soát.",
            "exclude_from_visualization": ASSETGROUP_VISUALIZATION_HELP_TEXT,
        }

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_code(self):
        return normalize_text(self.cleaned_data["code"])

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))

    def clean_comments(self):
        return normalize_text(self.cleaned_data.get("comments"))


class AssetGroupFilterForm(NetBoxModelFilterSetForm):
    model = AssetGroup
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("name", "code", "status", name="Nhóm tài sản"),
    )
    selector_fields = ("filter_id", "q", "status")

    name = forms.CharField(required=False, label="Tên")
    code = forms.CharField(required=False, label="Mã")
    status = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(AssetGroup.STATUS_CHOICES, ASSET_GROUP_STATUS_LABELS),
        label="Trạng thái",
    )
    tag = TagFilterField(model)


class AssetGroupImportForm(NetBoxModelImportForm):
    exclude_from_visualization = forms.BooleanField(
        required=False,
        label="Exclude from Visualization",
        help_text=ASSETGROUP_VISUALIZATION_HELP_TEXT,
    )
    status = CSVChoiceField(
        choices=choices_with_labels(AssetGroup.STATUS_CHOICES, ASSET_GROUP_STATUS_LABELS),
        help_text="Một trong các giá trị: active hoặc inactive.",
    )

    class Meta:
        model = AssetGroup
        fields = ("name", "slug", "code", "status", "exclude_from_visualization", "description", "comments")
        labels = {
            "name": "Tên",
            "code": "Mã",
            "status": "Trạng thái",
            "exclude_from_visualization": "Exclude from Visualization",
            "description": "Mô tả",
            "comments": "Ghi chú",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        translate_import_common_fields(self)

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_code(self):
        return normalize_text(self.cleaned_data["code"])

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))

    def clean_comments(self):
        return normalize_text(self.cleaned_data.get("comments"))


class SmartLockForm(UploadFileFormMixin, NetBoxModelForm):
    upload_file_model_name = "smartlock"
    request_user = None

    asset_group = DynamicModelChoiceField(
        queryset=AssetGroup.objects.filter(status=AssetGroup.STATUS_ACTIVE),
        label="Nhóm tài sản",
    )
    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=True,
        label="Khu vực",
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=True,
        label="Địa điểm",
        query_params={"region_id": "$region"},
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=True,
        label="Vị trí",
        query_params={"site_id": "$site"},
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.select_related("site", "location"),
        required=False,
        label="Tủ rack",
        query_params={"site_id": "$site", "location_id": "$location"},
        help_text="Khi chọn tủ rack, plugin sẽ kiểm tra và đồng bộ Địa điểm/Vị trí/Khu vực từ tủ rack.",
    )
    rack_face = forms.ChoiceField(
        required=False,
        label="Mặt tủ rack",
        choices=(("", "---------"),) + choices_with_labels(SmartLock.RACK_FACE_CHOICES, RACK_FACE_LABELS),
    )

    fieldsets = (
        FieldSet("name", "code", "asset_group", "status", name="Thông tin chính"),
        FieldSet("device_type", "model", "serial", "manufacturer", name="Thiết bị"),
        FieldSet("setup_date", "bought_date", "warranty_period", "warranty_expiration_preview", name="Vòng đời và bảo hành"),
        FieldSet("region", "site", "location", "rack", "rack_face", name="Vị trí"),
        FieldSet("description", "comments", "upload_files", "tags", name="Dữ liệu bổ sung"),
    )

    class Meta:
        model = SmartLock
        fields = (
            "name", "code", "asset_group", "status",
            "device_type", "model", "serial", "manufacturer",
            "setup_date", "bought_date", "warranty_period",
            "region", "site", "location", "rack", "rack_face",
            "description", "comments", "tags",
        )
        labels = {
            "name": "Tên",
            "code": "Mã",
            "status": "Trạng thái",
            "device_type": "Loại thiết bị",
            "model": "Model",
            "serial": "Serial",
            "manufacturer": "Nhà sản xuất",
            "setup_date": "Ngày lắp đặt",
            "bought_date": "Ngày mua",
            "warranty_period": "Thời hạn bảo hành",
            "description": "Mô tả",
            "comments": "Ghi chú",
        }
        widgets = {
            "setup_date": forms.DateInput(attrs={"type": "date"}),
            "bought_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "comments": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "code": "Mã duy nhất dùng cho nhập/xuất dữ liệu và đối soát tài sản.",
            "warranty_period": "Tính theo tháng. Hệ thống tự tính ngày hết hạn bảo hành.",
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_asset_group_field(self, self.request_user)
        restrict_dcim_scope_fields(self, self.request_user)
        self.fields["warranty_period"].help_text = "Đơn vị: tháng"
        self.fields["warranty_expiration_preview"] = forms.DateField(
            required=False,
            label="Ngày hết hạn bảo hành",
            disabled=True,
            initial=getattr(self.instance, "warranty_expiration_date", None),
            widget=forms.DateInput(attrs={"type": "date"}),
        )

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        return normalize_smartlock_form_data(self.instance, cleaned_data)

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_code(self):
        return normalize_text(self.cleaned_data["code"])

    def clean_device_type(self):
        return normalize_text(self.cleaned_data["device_type"])

    def clean_model(self):
        return normalize_text(self.cleaned_data.get("model"))

    def clean_serial(self):
        return normalize_text(self.cleaned_data.get("serial"))

    def clean_manufacturer(self):
        return normalize_text(self.cleaned_data.get("manufacturer"))

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))

    def clean_comments(self):
        return normalize_text(self.cleaned_data.get("comments"))


class SmartLockFilterForm(NetBoxModelFilterSetForm):
    model = SmartLock
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("name", "code", "status", "asset_group_id", "warranty_state", name="Thông tin chính"),
        FieldSet("device_type", "manufacturer", "serial", "device_model", name="Thiết bị"),
        FieldSet("region_id", "site_id", "location_id", "rack_id", "rack_face", name="Vị trí"),
    )
    selector_fields = (
        "filter_id", "q", "status", "asset_group_id", "warranty_state",
        "site_id", "location_id", "rack_id",
    )

    name = forms.CharField(required=False, label="Tên")
    code = forms.CharField(required=False, label="Mã")
    status = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(SmartLock.STATUS_CHOICES, SMARTLOCK_STATUS_LABELS),
        label="Trạng thái",
    )
    asset_group_id = DynamicModelMultipleChoiceField(
        queryset=AssetGroup.objects.all(),
        required=False,
        label="Nhóm tài sản",
    )
    warranty_state = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(WARRANTY_STATE_CHOICES, WARRANTY_STATE_LABELS),
        label="Trạng thái bảo hành",
    )
    device_type = forms.CharField(required=False, label="Loại thiết bị")
    manufacturer = forms.CharField(required=False, label="Nhà sản xuất")
    serial = forms.CharField(required=False, label="Serial")
    device_model = forms.CharField(required=False, label="Model")
    region_id = DynamicModelMultipleChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Khu vực",
    )
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Địa điểm",
        query_params={"region_id": "$region_id"},
    )
    location_id = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Vị trí",
        query_params={"site_id": "$site_id"},
    )
    rack_id = DynamicModelMultipleChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        label="Tủ rack",
        query_params={"site_id": "$site_id", "location_id": "$location_id"},
    )
    rack_face = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(SmartLock.RACK_FACE_CHOICES, RACK_FACE_LABELS),
        label="Mặt tủ rack",
    )
    tag = TagFilterField(model)


class SmartLockImportForm(NetBoxModelImportForm):
    request_user = None

    asset_group = CSVModelChoiceField(
        queryset=AssetGroup.objects.filter(status=AssetGroup.STATUS_ACTIVE),
        to_field_name="slug",
        help_text="Slug của nhóm tài sản.",
    )
    status = CSVChoiceField(
        choices=choices_with_labels(SmartLock.STATUS_CHOICES, SMARTLOCK_STATUS_LABELS),
        help_text="Một trong các giá trị: active, backup, maintenance, broken.",
    )
    region = CSVModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug khu vực. Có thể suy ra từ ánh xạ tủ rack/địa điểm.",
    )
    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug địa điểm. Có thể suy ra từ ánh xạ tủ rack/vị trí.",
    )
    location = CSVModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug vị trí. Có thể suy ra từ ánh xạ tủ rack.",
    )
    rack_face = CSVChoiceField(
        required=False,
        choices=choices_with_labels(SmartLock.RACK_FACE_CHOICES, RACK_FACE_LABELS),
        help_text="Một trong các giá trị: front hoặc rear.",
    )
    rack_lookup = forms.CharField(
        required=False,
        label="Tra cứu tủ rack",
        help_text="Định dạng: rack, site|rack hoặc site|location|rack.",
    )
    rack = forms.Field(required=False, widget=forms.HiddenInput)

    class Meta:
        model = SmartLock
        fields = SMARTLOCK_IMPORT_MODEL_FIELDS
        labels = {
            "name": "Tên",
            "code": "Mã",
            "asset_group": "Nhóm tài sản",
            "status": "Trạng thái",
            "description": "Mô tả",
            "comments": "Ghi chú",
            "device_type": "Loại thiết bị",
            "model": "Model",
            "serial": "Serial",
            "manufacturer": "Nhà sản xuất",
            "setup_date": "Ngày lắp đặt",
            "bought_date": "Ngày mua",
            "warranty_period": "Thời hạn bảo hành",
            "region": "Khu vực",
            "site": "Địa điểm",
            "location": "Vị trí",
            "rack_face": "Mặt tủ rack",
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_asset_group_field(self, self.request_user)
        restrict_dcim_scope_fields(self, self.request_user)
        translate_import_common_fields(self)
        self.fields["warranty_period"].help_text = "Đơn vị: tháng"

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        cleaned_data = normalize_smartlock_import_data(self.instance, cleaned_data)
        for field_name in ("region", "site", "location"):
            if not object_in_user_scope(cleaned_data.get(field_name), self.request_user):
                self.add_error(field_name, "Vui lòng chọn một giá trị hợp lệ trong danh sách cho phép.")
        if not object_in_user_scope(cleaned_data.get("rack"), self.request_user):
            self.add_error("rack_lookup", "Vui lòng chọn một giá trị hợp lệ trong danh sách cho phép.")
        return cleaned_data


class DeviceAssetFileForm(UploadFileFormMixin, NetBoxModelForm):
    upload_file_model_name = "asset"
    upload_file_label = "File đính kèm"

    fieldsets = (
        FieldSet("upload_files", name="File đính kèm"),
    )

    class Meta:
        model = Asset
        fields = ()


class DeviceAssetForm(UploadFileFormMixin, NetBoxModelForm):
    """Form tài sản nghiệp vụ độc lập theo DICM."""

    upload_file_model_name = "asset"
    request_user = None

    asset_group = DynamicModelChoiceField(
        queryset=AssetGroup.objects.filter(status=AssetGroup.STATUS_ACTIVE),
        label="Nhóm tài sản",
    )
    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Khu vực",
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Địa điểm",
        query_params={"region_id": "$region"},
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Vị trí",
        query_params={"site_id": "$site"},
    )

    fieldsets = (
        FieldSet("name", "code", "asset_group", "status", name="Thông tin chính"),
        FieldSet("device_type", "model", "serial", "manufacturer", name="Thiết bị"),
        FieldSet("setup_date", "bought_date", "warranty_period", "warranty_expiration_preview", name="Vòng đời và bảo hành"),
        FieldSet("region", "site", "location", name="Vị trí"),
        FieldSet("description", "comments", "upload_files", "tags", name="Dữ liệu bổ sung"),
    )

    class Meta:
        model = Asset
        fields = (
            "name", "code", "asset_group", "status",
            "device_type", "model", "serial", "manufacturer",
            "setup_date", "bought_date", "warranty_period",
            "region", "site", "location",
            "description", "comments", "tags",
        )
        labels = {
            "name": "Tên",
            "code": "Mã",
            "status": "Trạng thái",
            "device_type": "Loại thiết bị",
            "model": "Model",
            "serial": "Serial",
            "manufacturer": "Hãng sản xuất",
            "setup_date": "Ngày lắp đặt",
            "bought_date": "Ngày mua",
            "warranty_period": "Thời hạn bảo hành",
            "description": "Mô tả",
            "comments": "Ghi chú",
        }
        widgets = {
            "setup_date": forms.DateInput(attrs={"type": "date"}),
            "bought_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "comments": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "code": "Mã tài sản là bắt buộc, tối đa 50 ký tự và duy nhất.",
            "warranty_period": "Đơn vị: tháng. Hệ thống tự tính ngày hết hạn bảo hành.",
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_asset_group_field(self, self.request_user)
        restrict_dcim_scope_fields(self, self.request_user)
        self.fields["warranty_expiration_preview"] = forms.DateField(
            required=False,
            label="Ngày hết hạn bảo hành",
            disabled=True,
            initial=getattr(self.instance, "warranty_expiration_date", None),
            widget=forms.DateInput(attrs={"type": "date"}),
        )

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_code(self):
        return normalize_text(self.cleaned_data["code"])

    def clean_device_type(self):
        return normalize_text(self.cleaned_data["device_type"])

    def clean_model(self):
        return normalize_text(self.cleaned_data.get("model"))

    def clean_serial(self):
        return normalize_text(self.cleaned_data.get("serial"))

    def clean_manufacturer(self):
        return normalize_text(self.cleaned_data.get("manufacturer"))

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))

    def clean_comments(self):
        return normalize_text(self.cleaned_data.get("comments"))


class DeviceAssetFilterForm(NetBoxModelFilterSetForm):
    model = Asset
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("name", "code", "status", "asset_group_id", name="Thông tin chính"),
        FieldSet("site_id", "location_id", name="Vị trí"),
    )
    selector_fields = (
        "filter_id", "q", "status", "asset_group_id",
        "site_id", "location_id",
    )

    name = forms.CharField(required=False, label="Tên")
    code = forms.CharField(required=False, label="Mã")
    status = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(Asset.STATUS_CHOICES, ASSET_STATUS_LABELS),
        label="Trạng thái",
    )
    asset_group_id = DynamicModelMultipleChoiceField(
        queryset=AssetGroup.objects.all(),
        required=False,
        label="Nhóm tài sản",
    )
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Địa điểm",
    )
    location_id = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Vị trí",
        query_params={"site_id": "$site_id"},
    )
    tag = TagFilterField(model)


class AccessRequestForm(NetBoxModelForm):
    request_user = None

    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Khu vực",
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Địa điểm",
        query_params={"region_id": "$region"},
    )

    fieldsets = (
        FieldSet("name", "expected_date", name="Phiếu yêu cầu"),
        FieldSet("reason", name="Lý do"),
        FieldSet("region", "site", name="Phạm vi vị trí"),
        FieldSet("tags", name="Dữ liệu bổ sung"),
    )

    class Meta:
        model = AccessRequest
        fields = ("name", "expected_date", "reason", "region", "site", "tags")
        labels = {
            "name": "Tên phiếu",
            "expected_date": "Ngày dự kiến",
            "reason": "Lý do",
        }
        widgets = {
            "expected_date": forms.DateInput(attrs={"type": "date", "placeholder": "dd/mm/yyyy"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_dcim_scope_fields(self, self.request_user)

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_reason(self):
        return normalize_text(self.cleaned_data.get("reason"))


class AccessRequestFilterForm(NetBoxModelFilterSetForm):
    model = AccessRequest
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("name", "status", "region_id", "site_id", name="Phiếu yêu cầu vào ra"),
    )
    selector_fields = ("filter_id", "q", "status", "region_id", "site_id")

    name = forms.CharField(required=False, label="Tên phiếu")
    status = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(AccessRequest.STATUS_CHOICES, ACCESS_REQUEST_STATUS_LABELS),
        label="Trạng thái",
    )
    region_id = DynamicModelMultipleChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Khu vực",
    )
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Địa điểm",
        query_params={"region_id": "$region_id"},
    )
    tag = TagFilterField(model)


class AccessRequestBulkEditForm(NetBoxModelBulkEditForm):
    model = AccessRequest
    nullable_fields = ("region", "site")
    request_user = None

    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label="Khu vực")
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Địa điểm",
        query_params={"region_id": "$region"},
    )

    fieldsets = (
        FieldSet("pk", "region", "site", "add_tags", "remove_tags", "changelog_message", name="Phiếu yêu cầu vào ra"),
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_dcim_scope_fields(self, self.request_user)
        translate_bulk_common_fields(self)


class AccessRequestImportForm(NetBoxModelImportForm):
    request_user = None

    region = CSVModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug khu vực.",
    )
    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug địa điểm.",
    )

    class Meta:
        model = AccessRequest
        fields = ("name", "expected_date", "reason", "region", "site")
        labels = {
            "name": "Tên phiếu",
            "expected_date": "Ngày dự kiến",
            "reason": "Lý do",
            "region": "Khu vực",
            "site": "Địa điểm",
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_dcim_scope_fields(self, self.request_user)

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_reason(self):
        return normalize_text(self.cleaned_data.get("reason"))


class AccessRequestPersonForm(UploadFileFormMixin, NetBoxModelForm):
    upload_file_model_name = "accessrequestperson"
    request_user = None

    request = DynamicModelChoiceField(
        queryset=AccessRequest.objects.all(),
        label="Phiếu yêu cầu vào ra",
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Vị trí",
    )

    fieldsets = (
        FieldSet("request", "identity_code", "full_name", "organization", name="Đối tượng"),
        FieldSet("title", "phone", "location", name="Phạm vi vào ra"),
        FieldSet("description", "upload_files", "tags", name="Dữ liệu bổ sung"),
    )

    class Meta:
        model = AccessRequestPerson
        fields = (
            "request", "identity_code", "full_name", "organization", "title", "phone",
            "location", "description", "tags",
        )
        labels = {
            "identity_code": "CCCD/CMND",
            "full_name": "Họ tên",
            "organization": "Đơn vị",
            "title": "Chức danh",
            "phone": "Số điện thoại",
            "description": "Mô tả",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_dcim_scope_fields(self, self.request_user)
        if self.request_user is not None:
            self.fields["request"].queryset = restrict_access_requests_for_user(
                self.fields["request"].queryset,
                self.request_user,
            )
        request_id = self.initial.get("request") or getattr(self.instance, "request_id", None)
        if request_id:
            try:
                access_request = self.fields["request"].queryset.get(pk=request_id)
            except AccessRequest.DoesNotExist:
                access_request = None
            scope_location_field_to_access_request(self, access_request)
        else:
            enable_dynamic_location_scope(self)

    def clean_identity_code(self):
        return normalize_text(self.cleaned_data["identity_code"])

    def clean(self):
        super().clean()
        upload_files = self.cleaned_data.get(self.upload_file_field_name, "[]")

        # DICM yêu cầu mỗi đối tượng vào ra phải có ít nhất một file định danh đính kèm.
        add_required_upload_error(self, upload_files, instance=self.instance)

        access_request = self.cleaned_data.get("request")
        if self.request_user is not None and access_request and not user_can_access_request(self.request_user, access_request):
            self.add_error("request", ACCESS_REQUEST_PERSON_SCOPE_DENIED_MESSAGE)
        if access_request and not access_request.can_guest_edit:
            self.add_error("request", ACCESS_REQUEST_PERSON_EDIT_LOCKED_MESSAGE)

        return self.cleaned_data

    def clean_full_name(self):
        return normalize_text(self.cleaned_data["full_name"])

    def clean_organization(self):
        return normalize_text(self.cleaned_data["organization"])

    def clean_title(self):
        return normalize_text(self.cleaned_data.get("title"))

    def clean_phone(self):
        return normalize_text(self.cleaned_data.get("phone"))

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))


class AccessRequestPersonFilterForm(NetBoxModelFilterSetForm):
    model = AccessRequestPerson
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("request_id", "identity_code", "full_name", "verify_status", "access_status", name="Đối tượng"),
        FieldSet("organization", "location_id", name="Phạm vi"),
    )
    selector_fields = ("filter_id", "q", "request_id", "verify_status", "access_status", "location_id")

    request_id = DynamicModelMultipleChoiceField(
        queryset=AccessRequest.objects.all(),
        required=False,
        label="Phiếu yêu cầu vào ra",
    )
    identity_code = forms.CharField(required=False, label="CCCD/CMND")
    full_name = forms.CharField(required=False, label="Họ tên")
    organization = forms.CharField(required=False, label="Đơn vị")
    verify_status = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(AccessRequestPerson.VERIFY_STATUS_CHOICES, ACCESS_REQUEST_PERSON_VERIFY_LABELS),
        label="Trạng thái xác minh",
    )
    access_status = forms.MultipleChoiceField(
        required=False,
        choices=choices_with_labels(AccessRequestPerson.ACCESS_STATUS_CHOICES, ACCESS_REQUEST_PERSON_ACCESS_LABELS),
        label="Trạng thái vào ra",
    )
    location_id = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Vị trí",
    )
    tag = TagFilterField(model)


class AccessRequestPersonBulkEditForm(NetBoxModelBulkEditForm):
    model = AccessRequestPerson
    nullable_fields = ("title", "phone", "location", "description")
    request_user = None
    selected_persons_queryset = None

    title = forms.CharField(required=False, label="Chức danh")
    phone = forms.CharField(required=False, label="Số điện thoại")
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Vị trí",
    )
    description = forms.CharField(
        required=False,
        label="Mô tả",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    fieldsets = (
        FieldSet(
            "pk",
            "title",
            "phone",
            "location",
            "description",
            "add_tags",
            "remove_tags",
            "changelog_message",
            name="Đối tượng vào ra",
        ),
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_dcim_scope_fields(self, self.request_user)

        selected = self._selected_persons_queryset()
        site_ids = list(selected.values_list("request__site_id", flat=True).distinct())
        if len(site_ids) == 1 and site_ids[0]:
            self.fields["location"].queryset = self.fields["location"].queryset.filter(site_id=site_ids[0])
            if hasattr(self.fields["location"].widget, "add_query_param"):
                self.fields["location"].widget.add_query_param("site_id", str(site_ids[0]))

    def _selected_persons_queryset(self):
        """Dùng selected queryset để bulk edit Location chỉ trong cùng Site."""
        if self.__class__.selected_persons_queryset is not None:
            return self.__class__.selected_persons_queryset

        pk_list = []
        data = getattr(self, "data", None)
        if hasattr(data, "getlist"):
            pk_list = data.getlist("pk")
        elif data:
            raw_pk = data.get("pk")
            pk_list = raw_pk if isinstance(raw_pk, (list, tuple)) else [raw_pk]

        queryset = AccessRequestPerson.objects.select_related("request")
        if self.request_user is not None:
            queryset = restrict_access_request_persons_for_user(queryset, self.request_user)
        if pk_list:
            return queryset.filter(pk__in=pk_list)
        return queryset.none()

    def clean(self):
        cleaned_data = super().clean()
        location = self.cleaned_data.get("location")
        if location and self._selected_persons_queryset().exclude(request__site=location.site).exists():
            self.add_error("location", "Vị trí đã chọn phải thuộc địa điểm của tất cả phiếu yêu cầu được chọn.")
        return cleaned_data


class AccessRequestPersonImportForm(UploadFileFormMixin, NetBoxModelImportForm):
    upload_file_model_name = "accessrequestperson"
    request_user = None
    scoped_request_id = None

    request = CSVModelChoiceField(
        queryset=AccessRequest.objects.all(),
        required=False,
        to_field_name="id",
        help_text="ID phiếu yêu cầu. Có thể bỏ qua khi import từ tab chi tiết phiếu yêu cầu.",
    )
    location = CSVModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        to_field_name="id",
        help_text="ID vị trí.",
    )

    class Meta:
        model = AccessRequestPerson
        fields = (
            "request", "identity_code", "full_name", "organization",
            "title", "phone", "location", "description",
        )
        labels = {
            "request": "Phiếu yêu cầu vào ra",
            "identity_code": "CCCD/CMND",
            "full_name": "Họ tên",
            "organization": "Đơn vị",
            "title": "Chức danh",
            "phone": "Số điện thoại",
            "location": "Vị trí",
            "description": "Mô tả",
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        self.scoped_request_id = kwargs.pop("scoped_request_id", None) or self.__class__.scoped_request_id
        super().__init__(*args, **kwargs)
        restrict_dcim_scope_fields(self, self.request_user)
        if self.request_user is not None:
            self.fields["request"].queryset = restrict_access_requests_for_user(
                self.fields["request"].queryset,
                self.request_user,
            )
        if self.scoped_request_id:
            self.fields["request"].queryset = self.fields["request"].queryset.filter(pk=self.scoped_request_id)
        self.fields[self.upload_file_field_name].help_text = "Payload JSON file đính kèm được tạo bởi widget upload."
        translate_import_common_fields(self)

    def clean(self):
        super().clean()
        upload_files = self.cleaned_data.get(self.upload_file_field_name, "[]")
        add_required_upload_error(self, upload_files)

        access_request = self.cleaned_data.get("request")
        if access_request is None and self.scoped_request_id:
            try:
                access_request = self.fields["request"].queryset.get(pk=self.scoped_request_id)
                self.cleaned_data["request"] = access_request
            except AccessRequest.DoesNotExist:
                self.add_error("request", ACCESS_REQUEST_PERSON_SCOPED_REQUEST_UNAVAILABLE_MESSAGE)
        elif access_request is None:
            self.add_error("request", ACCESS_REQUEST_REQUIRED_MESSAGE)
        if self.request_user is not None and access_request and not user_can_access_request(self.request_user, access_request):
            self.add_error("request", ACCESS_REQUEST_PERSON_IMPORT_SCOPE_DENIED_MESSAGE)
        if access_request and not access_request.can_guest_edit:
            self.add_error("request", ACCESS_REQUEST_PERSON_IMPORT_LOCKED_MESSAGE)
        return self.cleaned_data

    def clean_identity_code(self):
        return normalize_text(self.cleaned_data["identity_code"])

    def clean_full_name(self):
        return normalize_text(self.cleaned_data["full_name"])

    def clean_organization(self):
        return normalize_text(self.cleaned_data["organization"])

    def clean_title(self):
        return normalize_text(self.cleaned_data.get("title"))

    def clean_phone(self):
        return normalize_text(self.cleaned_data.get("phone"))

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))
