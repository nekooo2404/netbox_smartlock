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
from .models import AccessRequest, AccessRequestPerson, AssetGroup, SmartLock
from .permissions import restrict_access_request_persons_for_user, restrict_access_requests_for_user, user_can_access_request
from .services import normalize_smartlock_form_data, normalize_smartlock_import_data
from .upload_files import files_for_object, upload_payload_has_valid_file


def restrict_dcim_scope_fields(form, user, action="view"):
    if user is None:
        return

    for field_name in ("region", "region_id", "site", "site_id", "location", "location_id", "rack", "rack_id"):
        field = form.fields.get(field_name)
        queryset = getattr(field, "queryset", None)
        if queryset is not None and hasattr(queryset, "restrict"):
            field.queryset = queryset.restrict(user, action)


def restrict_asset_group_field(form, user, action="view"):
    field = form.fields.get("asset_group")
    queryset = getattr(field, "queryset", None)
    if queryset is None:
        return

    queryset = queryset.filter(status=AssetGroup.STATUS_ACTIVE)
    if user is not None and hasattr(queryset, "restrict"):
        queryset = queryset.restrict(user, action)
    field.queryset = queryset


def object_in_user_scope(obj, user, action="view"):
    if obj is None or user is None:
        return True

    queryset = obj.__class__.objects.filter(pk=obj.pk)
    if hasattr(queryset, "restrict"):
        queryset = queryset.restrict(user, action)
    return queryset.exists()


class AssetGroupForm(UploadFileFormMixin, NetBoxModelForm):
    upload_file_model_name = "assetgroup"
    slug = SlugField()

    fieldsets = (
        FieldSet("name", "slug", "code", "status", name="Primary Information"),
        FieldSet("description", "comments", name="Description"),
        FieldSet("upload_files", "tags", name="Additional Data"),
    )

    class Meta:
        model = AssetGroup
        fields = ("name", "slug", "code", "status", "description", "comments", "tags")
        help_texts = {
            "code": "Group code for import/export and data reconciliation.",
        }

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_code(self):
        value = self.cleaned_data.get("code")
        return normalize_text(value) or None

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))

    def clean_comments(self):
        return normalize_text(self.cleaned_data.get("comments"))


class AssetGroupFilterForm(NetBoxModelFilterSetForm):
    model = AssetGroup
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("name", "code", "status", name="Asset Group"),
    )
    selector_fields = ("filter_id", "q", "status")

    name = forms.CharField(required=False, label="Name")
    code = forms.CharField(required=False, label="Code")
    status = forms.MultipleChoiceField(required=False, choices=AssetGroup.STATUS_CHOICES, label="Status")
    tag = TagFilterField(model)


class AssetGroupImportForm(NetBoxModelImportForm):
    status = CSVChoiceField(
        choices=AssetGroup.STATUS_CHOICES,
        help_text="One of: active or inactive.",
    )

    class Meta:
        model = AssetGroup
        fields = ("name", "slug", "code", "status", "description", "comments")

    def clean_name(self):
        return normalize_text(self.cleaned_data["name"])

    def clean_code(self):
        value = self.cleaned_data.get("code")
        return normalize_text(value) or None

    def clean_description(self):
        return normalize_text(self.cleaned_data.get("description"))

    def clean_comments(self):
        return normalize_text(self.cleaned_data.get("comments"))


class SmartLockForm(UploadFileFormMixin, NetBoxModelForm):
    upload_file_model_name = "smartlock"
    request_user = None

    asset_group = DynamicModelChoiceField(
        queryset=AssetGroup.objects.filter(status=AssetGroup.STATUS_ACTIVE),
        label="Asset Group",
    )
    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=True,
        label="Region",
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=True,
        label="Site",
        query_params={"region_id": "$region"},
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=True,
        label="Location",
        query_params={"site_id": "$site"},
    )
    rack = DynamicModelChoiceField(
        queryset=Rack.objects.select_related("site", "location"),
        required=False,
        label="Rack",
        query_params={"site_id": "$site", "location_id": "$location"},
        help_text="When Rack is selected, the plugin validates and synchronizes Site/Location/Region from the Rack.",
    )
    rack_face = forms.ChoiceField(
        required=False,
        label="Rack Face",
        choices=(("", "---------"),) + SmartLock.RACK_FACE_CHOICES,
    )

    fieldsets = (
        FieldSet("name", "code", "asset_group", "status", name="Primary Information"),
        FieldSet("device_type", "model", "serial", "manufacturer", name="Device"),
        FieldSet("setup_date", "bought_date", "warranty_period", "warranty_expiration_preview", name="Lifecycle and Warranty"),
        FieldSet("region", "site", "location", "rack", "rack_face", name="Location"),
        FieldSet("description", "comments", "upload_files", "tags", name="Additional Data"),
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
        widgets = {
            "setup_date": forms.DateInput(attrs={"type": "date"}),
            "bought_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "comments": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "code": "Unique code for import/export and asset reconciliation.",
            "warranty_period": "Measured in months. The system calculates the warranty expiration date automatically.",
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_asset_group_field(self, self.request_user)
        restrict_dcim_scope_fields(self, self.request_user)
        self.fields["warranty_expiration_preview"] = forms.DateField(
            required=False,
            label="Warranty Expiration Date",
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
        FieldSet("name", "code", "status", "asset_group_id", "warranty_state", name="Primary Information"),
        FieldSet("device_type", "manufacturer", "serial", "device_model", name="Device"),
        FieldSet("region_id", "site_id", "location_id", "rack_id", "rack_face", name="Location"),
    )
    selector_fields = (
        "filter_id", "q", "status", "asset_group_id", "warranty_state",
        "site_id", "location_id", "rack_id",
    )

    name = forms.CharField(required=False, label="Name")
    code = forms.CharField(required=False, label="Code")
    status = forms.MultipleChoiceField(required=False, choices=SmartLock.STATUS_CHOICES, label="Status")
    asset_group_id = DynamicModelMultipleChoiceField(
        queryset=AssetGroup.objects.all(),
        required=False,
        label="Asset Group",
    )
    warranty_state = forms.MultipleChoiceField(
        required=False,
        choices=WARRANTY_STATE_CHOICES,
        label="Warranty State",
    )
    device_type = forms.CharField(required=False, label="Device Type")
    manufacturer = forms.CharField(required=False, label="Manufacturer")
    serial = forms.CharField(required=False, label="Serial")
    device_model = forms.CharField(required=False, label="Model")
    region_id = DynamicModelMultipleChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Region",
    )
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Site",
        query_params={"region_id": "$region_id"},
    )
    location_id = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Location",
        query_params={"site_id": "$site_id"},
    )
    rack_id = DynamicModelMultipleChoiceField(
        queryset=Rack.objects.all(),
        required=False,
        label="Rack",
        query_params={"site_id": "$site_id", "location_id": "$location_id"},
    )
    rack_face = forms.MultipleChoiceField(required=False, choices=SmartLock.RACK_FACE_CHOICES, label="Rack Face")
    tag = TagFilterField(model)


class SmartLockImportForm(NetBoxModelImportForm):
    request_user = None

    asset_group = CSVModelChoiceField(
        queryset=AssetGroup.objects.filter(status=AssetGroup.STATUS_ACTIVE),
        to_field_name="slug",
        help_text="AssetGroup slug.",
    )
    status = CSVChoiceField(
        choices=SmartLock.STATUS_CHOICES,
        help_text="One of: active, backup, maintenance, broken.",
    )
    region = CSVModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Region slug. May be inferred from Rack/Site mapping.",
    )
    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Site slug. May be inferred from Rack/Location mapping.",
    )
    location = CSVModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Location slug. May be inferred from Rack mapping.",
    )
    rack_face = CSVChoiceField(
        required=False,
        choices=SmartLock.RACK_FACE_CHOICES,
        help_text="One of: front or rear.",
    )
    rack_lookup = forms.CharField(
        required=False,
        label="Rack lookup",
        help_text="Format: rack, site|rack, or site|location|rack.",
    )
    rack = forms.Field(required=False, widget=forms.HiddenInput)

    class Meta:
        model = SmartLock
        fields = SMARTLOCK_IMPORT_MODEL_FIELDS

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_asset_group_field(self, self.request_user)
        restrict_dcim_scope_fields(self, self.request_user)

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        cleaned_data = normalize_smartlock_import_data(self.instance, cleaned_data)
        for field_name in ("region", "site", "location"):
            if not object_in_user_scope(cleaned_data.get(field_name), self.request_user):
                self.add_error(field_name, "Select a valid choice. That choice is not one of the available choices.")
        if not object_in_user_scope(cleaned_data.get("rack"), self.request_user):
            self.add_error("rack_lookup", "Select a valid choice. That choice is not one of the available choices.")
        return cleaned_data


class AccessRequestForm(NetBoxModelForm):
    request_user = None

    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Region",
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Site",
        query_params={"region_id": "$region"},
    )

    fieldsets = (
        FieldSet("name", "expected_date", name="Request"),
        FieldSet("reason", name="Reason"),
        FieldSet("region", "site", name="Location Scope"),
        FieldSet("tags", name="Additional Data"),
    )

    class Meta:
        model = AccessRequest
        fields = ("name", "expected_date", "reason", "region", "site", "tags")
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
        FieldSet("name", "status", "region_id", "site_id", name="Access Request"),
    )
    selector_fields = ("filter_id", "q", "status", "region_id", "site_id")

    name = forms.CharField(required=False, label="Request Name")
    status = forms.MultipleChoiceField(required=False, choices=AccessRequest.STATUS_CHOICES, label="Status")
    region_id = DynamicModelMultipleChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label="Region",
    )
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Site",
        query_params={"region_id": "$region_id"},
    )
    tag = TagFilterField(model)


class AccessRequestBulkEditForm(NetBoxModelBulkEditForm):
    model = AccessRequest
    nullable_fields = ("region", "site")
    request_user = None

    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, label="Region")
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label="Site",
        query_params={"region_id": "$region"},
    )

    fieldsets = (
        FieldSet("pk", "region", "site", "add_tags", "remove_tags", "changelog_message", name="Access Request"),
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None) or self.__class__.request_user
        super().__init__(*args, **kwargs)
        restrict_dcim_scope_fields(self, self.request_user)


class AccessRequestImportForm(NetBoxModelImportForm):
    request_user = None

    region = CSVModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Region slug.",
    )
    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Site slug.",
    )

    class Meta:
        model = AccessRequest
        fields = ("name", "expected_date", "reason", "region", "site")

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
        label="Access Request",
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Location",
    )

    fieldsets = (
        FieldSet("request", "identity_code", "full_name", "organization", name="Person"),
        FieldSet("title", "phone", "location", name="Access Scope"),
        FieldSet("description", "upload_files", "tags", name="Additional Data"),
    )

    class Meta:
        model = AccessRequestPerson
        fields = (
            "request", "identity_code", "full_name", "organization", "title", "phone",
            "location", "description", "tags",
        )
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
            if access_request and access_request.site_id:
                self.fields["location"].queryset = self.fields["location"].queryset.filter(site=access_request.site)
                self.fields["location"].widget.add_query_param("site_id", str(access_request.site_id))
        else:
            self.fields["location"].widget.attrs["data-smartlock-request-field"] = "id_request"
            self.fields["location"].widget.attrs["data-smartlock-location-scope"] = "true"

    def clean_identity_code(self):
        return normalize_text(self.cleaned_data["identity_code"])

    def clean(self):
        super().clean()
        upload_files = self.cleaned_data.get(self.upload_file_field_name, "[]")

        if not upload_payload_has_valid_file(
            upload_files,
            instance=self.instance,
            model_name=self.upload_file_model_name,
        ):
            self.add_error(self.upload_file_field_name, "At least one attachment is required.")

        access_request = self.cleaned_data.get("request")
        if self.request_user is not None and access_request and not user_can_access_request(self.request_user, access_request):
            self.add_error("request", "You do not have permission to add persons to this access request.")
        if access_request and not access_request.can_guest_edit:
            self.add_error("request", "Persons cannot be added or edited after an access request is accepted or completed.")

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
        FieldSet("request_id", "identity_code", "full_name", "verify_status", "access_status", name="Person"),
        FieldSet("organization", "location_id", name="Scope"),
    )
    selector_fields = ("filter_id", "q", "request_id", "verify_status", "access_status", "location_id")

    request_id = DynamicModelMultipleChoiceField(
        queryset=AccessRequest.objects.all(),
        required=False,
        label="Access Request",
    )
    identity_code = forms.CharField(required=False, label="Identity Code")
    full_name = forms.CharField(required=False, label="Full Name")
    organization = forms.CharField(required=False, label="Organization")
    verify_status = forms.MultipleChoiceField(
        required=False,
        choices=AccessRequestPerson.VERIFY_STATUS_CHOICES,
        label="Verification Status",
    )
    access_status = forms.MultipleChoiceField(
        required=False,
        choices=AccessRequestPerson.ACCESS_STATUS_CHOICES,
        label="Access Status",
    )
    location_id = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Location",
    )
    tag = TagFilterField(model)


class AccessRequestPersonBulkEditForm(NetBoxModelBulkEditForm):
    model = AccessRequestPerson
    nullable_fields = ("title", "phone", "location", "description")
    request_user = None
    selected_persons_queryset = None

    title = forms.CharField(required=False, label="Title")
    phone = forms.CharField(required=False, label="Phone")
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Location",
    )
    description = forms.CharField(
        required=False,
        label="Description",
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
            name="Access Request Person",
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
            self.add_error("location", "Selected Location must belong to every selected Access Request Site.")
        return cleaned_data


class AccessRequestPersonImportForm(UploadFileFormMixin, NetBoxModelImportForm):
    upload_file_model_name = "accessrequestperson"
    request_user = None
    scoped_request_id = None

    request = CSVModelChoiceField(
        queryset=AccessRequest.objects.all(),
        required=False,
        to_field_name="id",
        help_text="Access Request ID. Optional when importing from an Access Request detail tab.",
    )
    location = CSVModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        to_field_name="id",
        help_text="Location ID.",
    )

    class Meta:
        model = AccessRequestPerson
        fields = (
            "request", "identity_code", "full_name", "organization",
            "title", "phone", "location", "description",
        )

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
        self.fields[self.upload_file_field_name].help_text = "JSON attachment payload created by the upload widget."

    def clean(self):
        super().clean()
        upload_files = self.cleaned_data.get(self.upload_file_field_name, "[]")
        if not upload_payload_has_valid_file(upload_files, model_name=self.upload_file_model_name):
            self.add_error(self.upload_file_field_name, "At least one attachment is required.")

        access_request = self.cleaned_data.get("request")
        if access_request is None and self.scoped_request_id:
            try:
                access_request = self.fields["request"].queryset.get(pk=self.scoped_request_id)
                self.cleaned_data["request"] = access_request
            except AccessRequest.DoesNotExist:
                self.add_error("request", "Scoped access request is not available.")
        elif access_request is None:
            self.add_error("request", "Access Request is required.")
        if self.request_user is not None and access_request and not user_can_access_request(self.request_user, access_request):
            self.add_error("request", "You do not have permission to import persons to this access request.")
        if access_request and not access_request.can_guest_edit:
            self.add_error("request", "Persons cannot be imported after an access request is accepted or completed.")
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
