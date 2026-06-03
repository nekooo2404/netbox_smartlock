from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.choices import ObjectChangeActionChoices
from core.models.change_logging import ObjectChange
from core.tables import ObjectChangeTable
from netbox.views.generic import (
    BulkImportView,
    BulkDeleteView,
    BulkEditView,
    BulkRenameView,
    ObjectChangeLogView,
    ObjectDeleteView,
    ObjectEditView,
    ObjectListView,
    ObjectView,
)
from netbox.object_actions import (
    AddObject,
    BulkDelete,
    BulkEdit,
    BulkImport,
    BulkRename,
    CloneObject,
    DeleteObject,
    EditObject,
)

from .change_logging import annotate_creator
from .contracts import SMARTLOCK_IMPORT_CSV_DESCRIPTION, SMARTLOCK_IMPORT_HELP_ITEMS
from .exports import AccessRequestExportService, AssetGroupExportService, DeviceAssetExportService, SmartLockExportService
from .filtersets import (
    AccessRequestFilterSet,
    AccessRequestPersonFilterSet,
    AssetGroupFilterSet,
    DeviceAssetFilterSet,
    SmartLockFilterSet,
)
from .forms import (
    AccessRequestBulkEditForm,
    AccessRequestFilterForm,
    AccessRequestForm,
    AccessRequestImportForm,
    AccessRequestPersonFilterForm,
    AccessRequestPersonBulkEditForm,
    AccessRequestPersonForm,
    AccessRequestPersonImportForm,
    AssetGroupFilterForm,
    AssetGroupForm,
    AssetGroupImportForm,
    DeviceAssetForm,
    DeviceAssetFileForm,
    DeviceAssetFilterForm,
    SmartLockFilterForm,
    SmartLockForm,
    SmartLockImportForm,
)
from .labels import apply_model_label_context
from .mapping import format_rack_lookup, get_warranty_state
from .messages import (
    ACCESS_REQUEST_ADMIN_CRUD_MESSAGE,
    ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE,
    ACCESS_REQUEST_GUEST_EDIT_DENIED_MESSAGE,
    ACCESS_REQUEST_OBJECT_WORKFLOW_PERMISSION_MESSAGE,
    ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE,
    ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE,
    ACCESS_REQUEST_PERSON_EDIT_DENIED_MESSAGE,
    ACCESS_REQUEST_PERSON_OBJECT_WORKFLOW_PERMISSION_MESSAGE,
    ACCESS_REQUEST_PERSON_WORKFLOW_PERMISSION_MESSAGE,
    ACCESS_REQUEST_SEND_PERMISSION_MESSAGE,
    ACCESS_REQUEST_WORKFLOW_PERMISSION_MESSAGE,
)
from .models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock
from .permissions import (
    can_manage_access_request,
    can_manage_access_request_person,
    can_manage_access_request_persons,
    can_manage_access_requests,
    can_submit_access_request,
    is_access_request_admin,
    restrict_access_request_persons_for_user,
    restrict_access_requests_for_user,
)
from .shared_asset_groups import asset_group_device_filter_url, assets_for_asset_group
from .tables import AccessRequestPersonTable, AccessRequestTable, AssetGroupTable, DeviceAssetTable, SmartLockTable
from .ui import (
    ACCESS_REQUEST_PERSON_ACCESS_LABELS,
    ACCESS_REQUEST_PERSON_VERIFY_LABELS,
    ACCESS_REQUEST_STATUS_LABELS,
    RACK_FACE_LABELS,
    SMARTLOCK_STATUS_LABELS,
    DEVICE_ASSET_LIST_ACTIONS,
    VIETNAMESE_DETAIL_ACTIONS,
    VIETNAMESE_DETAIL_ACTIONS_WITHOUT_CLONE,
    VIETNAMESE_LIST_ACTIONS,
    VIETNAMESE_LIST_ACTIONS_WITHOUT_RENAME,
    WARRANTY_STATE_LABELS,
    label_for,
    warranty_state_badge,
)
from .upload_files import annotate_file_count, files_for_object
from utilities.views import get_default_template, safe_for_redirect


def request_scoped_form(form_class, **attrs):
    """Tạo form class theo request để giữ tương thích với generic view của NetBox."""
    return type(f"RequestScoped{form_class.__name__}", (form_class,), attrs)


def enforce_guest_crud_access(user, message):
    if is_access_request_admin(user):
        raise PermissionDenied(message)


def filter_guest_object_actions(actions, instance):
    """Ẩn nút sửa/xóa ở UI khi object đang ở trạng thái Guest không được thao tác."""
    filtered_actions = []
    for action in actions:
        if issubclass(action, EditObject) and not getattr(instance, "can_guest_edit", True):
            continue
        if issubclass(action, DeleteObject) and not getattr(instance, "can_guest_delete", True):
            continue
        filtered_actions.append(action)
    return tuple(filtered_actions)


def filter_access_request_actions_for_user(actions, user, instance_or_model=None):
    """Admin dùng workflow riêng nên không hiển thị CRUD thường trên phiếu/đối tượng."""
    if not is_access_request_admin(user):
        if instance_or_model is not None and not isinstance(instance_or_model, type):
            return filter_guest_object_actions(actions, instance_or_model)
        return actions

    blocked_actions = (AddObject, BulkImport, BulkEdit, BulkRename, BulkDelete, CloneObject, EditObject, DeleteObject)
    return tuple(action for action in actions if not any(issubclass(action, blocked) for blocked in blocked_actions))


class VietnameseModelLabelMixin:
    """Bổ sung label tiếng Việt cho template dùng lại generic của NetBox."""

    def get_extra_context(self, request, instance=None):
        try:
            if instance is not None:
                context = super().get_extra_context(request, instance)
            else:
                context = super().get_extra_context(request)
        except AttributeError:
            context = {}

        target = instance
        if target is None:
            target = getattr(self, "model", None)
        if target is None:
            target = getattr(getattr(self, "queryset", None), "model", None)

        return apply_model_label_context(context or {}, target)


class ScopedObjectChangeLogView(ObjectChangeLogView):
    """Object changelog view using a plugin-scoped parent object queryset."""

    def get_parent_queryset(self, request, model):
        if hasattr(model.objects, "restrict"):
            return model.objects.restrict(request.user, "view")
        return model.objects.all()

    def get(self, request, model, **kwargs):
        obj = get_object_or_404(self.get_parent_queryset(request, model), **kwargs)
        content_type = ContentType.objects.get_for_model(model)
        objectchanges = (
            ObjectChange.objects.restrict(request.user, "view")
            .prefetch_related("user", "changed_object_type")
            .filter(
                Q(changed_object_type=content_type, changed_object_id=obj.pk)
                | Q(related_object_type=content_type, related_object_id=obj.pk)
            )
        )
        objectchanges_table = ObjectChangeTable(
            data=objectchanges,
            orderable=False,
        )
        objectchanges_table.configure(request)

        return render(
            request,
            "extras/object_changelog.html",
            {
                "object": obj,
                "table": objectchanges_table,
                "base_template": self.base_template or get_default_template(model),
                "tab": self.tab,
            },
        )


class AccessRequestAdminCrudGuardMixin:
    admin_crud_message = ACCESS_REQUEST_ADMIN_CRUD_MESSAGE

    def dispatch(self, request, *args, **kwargs):
        enforce_guest_crud_access(request.user, self.admin_crud_message)
        return super().dispatch(request, *args, **kwargs)


class AssetGroupListView(ObjectListView):
    queryset = annotate_file_count(
        annotate_creator(AssetGroup.objects.prefetch_related("tags")),
        model_name="assetgroup",
    )
    table = AssetGroupTable
    filterset = AssetGroupFilterSet
    filterset_form = AssetGroupFilterForm
    template_name = "netbox_smartlock/assetgroup_list.html"
    actions = VIETNAMESE_LIST_ACTIONS_WITHOUT_RENAME

    def get_extra_context(self, request):
        context = AssetGroupExportService.build_control_urls(request)
        return apply_model_label_context(context, AssetGroup)

    def get(self, request):
        if AssetGroupExportService.is_custom_export_request(request):
            if self.filterset:
                self.queryset = self.filterset(request.GET, self.queryset, request=request).qs
            return AssetGroupExportService.dispatch_custom_export(
                request,
                view=self,
                queryset=self.queryset,
            )

        return super().get(request)


class AssetGroupView(ObjectView):
    queryset = AssetGroup.objects.prefetch_related("tags")
    template_name = "netbox_smartlock/assetgroup.html"
    actions = VIETNAMESE_DETAIL_ACTIONS

    def get_extra_context(self, request, instance):
        smartlocks = instance.smartlocks.select_related("site", "location", "rack").prefetch_related("tags")
        device_assets = assets_for_asset_group(instance, request.user)
        return apply_model_label_context({
            "device_assets": device_assets[:10],
            "device_assets_count": device_assets.count(),
            "device_assets_list_url": asset_group_device_filter_url(instance),
            "smartlocks": smartlocks[:10],
            "smartlocks_count": smartlocks.count(),
            "smartlocks_list_url": (
                f"{reverse('plugins:netbox_smartlock:smartlock_list')}?asset_group_id={instance.pk}"
            ),
            "uploaded_files": files_for_object(instance, model_name="assetgroup"),
        }, instance)


class AssetGroupEditView(VietnameseModelLabelMixin, ObjectEditView):
    queryset = AssetGroup.objects.all()
    form = AssetGroupForm
    template_name = "netbox_smartlock/object_edit_cancel_confirm.html"


class AssetGroupImportView(VietnameseModelLabelMixin, BulkImportView):
    queryset = AssetGroup.objects.all()
    model_form = AssetGroupImportForm
    template_name = "netbox_smartlock/bulk_import.html"


class AssetGroupDeleteView(VietnameseModelLabelMixin, ObjectDeleteView):
    queryset = AssetGroup.objects.all()
    template_name = "netbox_smartlock/object_delete.html"


class AssetGroupChangeLogView(ScopedObjectChangeLogView):
    queryset = AssetGroup.objects.all()


class DeviceAssetListView(ObjectListView):
    queryset = annotate_creator(
        annotate_file_count(
            Asset.objects.select_related(
                "asset_group", "device", "device__device_type__manufacturer",
                "device__site", "device__location", "device__rack",
            ).prefetch_related("tags"),
            model_name="asset",
        )
    )
    table = DeviceAssetTable
    filterset = DeviceAssetFilterSet
    filterset_form = DeviceAssetFilterForm
    template_name = "netbox_smartlock/device_asset_list.html"
    actions = DEVICE_ASSET_LIST_ACTIONS

    def get_extra_context(self, request):
        context = DeviceAssetExportService.build_control_urls(request)
        context.update(
            {
                "smartlock_model_label": "tài sản",
                "smartlock_model_label_plural": "tài sản",
            }
        )
        return apply_model_label_context(
            context,
            Asset,
        )

    def get(self, request):
        if DeviceAssetExportService.is_custom_export_request(request):
            if self.filterset:
                self.queryset = self.filterset(request.GET, self.queryset, request=request).qs
            return DeviceAssetExportService.dispatch_custom_export(
                request,
                view=self,
                queryset=self.queryset,
            )

        return super().get(request)


class DeviceAssetView(ObjectView):
    queryset = Asset.objects.select_related(
        "asset_group", "device", "device__device_type__manufacturer",
        "device__site", "device__location", "device__rack",
    ).prefetch_related("tags")
    template_name = "netbox_smartlock/device_asset.html"
    actions = VIETNAMESE_DETAIL_ACTIONS_WITHOUT_CLONE

    def get_extra_context(self, request, instance):
        warranty_state = get_warranty_state(instance.warranty_expiration_date)
        content_type = ContentType.objects.get_for_model(instance)
        creator = (
            ObjectChange.objects.filter(
                changed_object_type=content_type,
                changed_object_id=instance.pk,
                action=ObjectChangeActionChoices.ACTION_CREATE,
            )
            .order_by("time")
            .values_list("user_name", flat=True)
            .first()
        )
        return apply_model_label_context({
            "device": instance.device,
            "uploaded_files": files_for_object(instance, model_name="asset"),
            "warranty_state": warranty_state,
            "warranty_state_badge": warranty_state_badge(warranty_state),
            "warranty_state_label": label_for(WARRANTY_STATE_LABELS, warranty_state),
            "asset_status_label": label_for(SMARTLOCK_STATUS_LABELS, instance.status),
            "created_by_name": creator or "-",
        }, instance)


class DeviceAssetEditView(VietnameseModelLabelMixin, ObjectEditView):
    queryset = Asset.objects.select_related("device", "asset_group")
    form = DeviceAssetForm
    template_name = "netbox_smartlock/object_edit_cancel_confirm.html"
    default_return_url = "plugins:netbox_smartlock:device_asset_list"

    def dispatch(self, request, *args, **kwargs):
        self.form = request_scoped_form(DeviceAssetForm, request_user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_return_url(self, request, obj=None):
        return_url = request.GET.get("return_url") or request.POST.get("return_url")
        if return_url and safe_for_redirect(return_url):
            return return_url
        return reverse(self.default_return_url)

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        context.update({
            "smartlock_model_label": "tài sản",
            "smartlock_model_label_plural": "tài sản",
        })
        return context


class DeviceAssetDeleteView(VietnameseModelLabelMixin, ObjectDeleteView):
    queryset = Asset.objects.select_related("device", "asset_group")
    template_name = "netbox_smartlock/object_delete.html"
    default_return_url = "plugins:netbox_smartlock:device_asset_list"

    def get_return_url(self, request, obj=None):
        return_url = request.GET.get("return_url") or request.POST.get("return_url")
        if return_url and safe_for_redirect(return_url):
            return return_url
        return reverse(self.default_return_url)

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        context.update({
            "smartlock_model_label": "tài sản",
            "smartlock_model_label_plural": "tài sản",
        })
        return context


class DeviceAssetFileView(VietnameseModelLabelMixin, ObjectEditView):
    queryset = Asset.objects.select_related("device", "asset_group")
    form = DeviceAssetFileForm
    template_name = "netbox_smartlock/device_asset_files.html"

    def get_queryset(self, request):
        return super().get_queryset(request).restrict(request.user, "view")

    def get_object(self, **kwargs):
        asset = super().get_object(**kwargs)
        if self.request.method == "POST" and not self.queryset.restrict(self.request.user, "change").filter(
            pk=asset.pk
        ).exists():
            raise PermissionDenied("Bạn không có quyền cập nhật file đính kèm của tài sản này.")
        return asset

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        context.update({
            "device": instance.device if instance else None,
            "uploaded_files": files_for_object(instance, model_name="asset") if instance else (),
            "return_url": instance.get_absolute_url() if instance else reverse("plugins:netbox_smartlock:device_asset_list"),
            "smartlock_model_label": "file đính kèm tài sản",
        })
        return context


class SmartLockListView(ObjectListView):
    queryset = annotate_creator(
        annotate_file_count(
            SmartLock.objects.select_related(
                "asset_group", "region", "site", "location", "rack"
            ).prefetch_related("tags"),
            model_name="smartlock",
        )
    )
    table = SmartLockTable
    filterset = SmartLockFilterSet
    filterset_form = SmartLockFilterForm
    template_name = "netbox_smartlock/smartlock_list.html"
    actions = VIETNAMESE_LIST_ACTIONS_WITHOUT_RENAME

    def get_extra_context(self, request):
        context = SmartLockExportService.build_control_urls(request)
        return apply_model_label_context(context, SmartLock)

    def export_table(self, table, columns=None, filename=None, delimiter=None):
        return SmartLockExportService.export_core_csv(
            self.queryset,
            filename=filename,
            delimiter=delimiter,
        )

    def get(self, request):
        if SmartLockExportService.is_custom_export_request(request):
            if self.filterset:
                self.queryset = self.filterset(request.GET, self.queryset, request=request).qs
            return SmartLockExportService.dispatch_custom_export(
                request,
                view=self,
                queryset=self.queryset,
            )

        return super().get(request)


class SmartLockView(ObjectView):
    queryset = SmartLock.objects.select_related(
        "asset_group", "region", "site", "location", "rack"
    ).prefetch_related("tags")
    actions = VIETNAMESE_DETAIL_ACTIONS

    def get_extra_context(self, request, instance):
        warranty_state = get_warranty_state(instance.warranty_expiration_date)
        content_type = ContentType.objects.get_for_model(instance)
        creator = (
            ObjectChange.objects.filter(
                changed_object_type=content_type,
                changed_object_id=instance.pk,
                action=ObjectChangeActionChoices.ACTION_CREATE,
            )
            .order_by("time")
            .values_list("user_name", flat=True)
            .first()
        )
        return apply_model_label_context({
            "uploaded_files": files_for_object(instance, model_name="smartlock"),
            "rack_lookup": format_rack_lookup(instance.rack),
            "warranty_state": warranty_state,
            "warranty_state_badge": warranty_state_badge(warranty_state),
            "warranty_state_label": label_for(WARRANTY_STATE_LABELS, warranty_state),
            "smartlock_status_label": label_for(SMARTLOCK_STATUS_LABELS, instance.status),
            "rack_face_label": label_for(RACK_FACE_LABELS, instance.rack_face),
            "created_by_name": creator or "-",
        }, instance)


class SmartLockEditView(VietnameseModelLabelMixin, ObjectEditView):
    queryset = SmartLock.objects.all()
    form = SmartLockForm
    template_name = "netbox_smartlock/object_edit_cancel_confirm.html"

    def dispatch(self, request, *args, **kwargs):
        self.form = request_scoped_form(SmartLockForm, request_user=request.user)
        return super().dispatch(request, *args, **kwargs)


class SmartLockImportView(VietnameseModelLabelMixin, BulkImportView):
    queryset = SmartLock.objects.all()
    model_form = SmartLockImportForm
    template_name = "netbox_smartlock/bulk_import.html"

    def dispatch(self, request, *args, **kwargs):
        self.model_form = request_scoped_form(SmartLockImportForm, request_user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_extra_context(self, request):
        context = super().get_extra_context(request)
        context.update({
            "csv_description": SMARTLOCK_IMPORT_CSV_DESCRIPTION,
            "csv_help_items": SMARTLOCK_IMPORT_HELP_ITEMS,
        })
        return context


class SmartLockDeleteView(VietnameseModelLabelMixin, ObjectDeleteView):
    queryset = SmartLock.objects.all()
    template_name = "netbox_smartlock/object_delete.html"


class SmartLockChangeLogView(ScopedObjectChangeLogView):
    queryset = SmartLock.objects.all()


class AccessRequestListView(ObjectListView):
    queryset = annotate_creator(
        AccessRequest.objects.select_related("region", "site")
        .prefetch_related("tags")
        .annotate(person_count=Count("persons"))
    )
    table = AccessRequestTable
    filterset = AccessRequestFilterSet
    filterset_form = AccessRequestFilterForm
    template_name = "netbox_smartlock/accessrequest_list.html"
    actions = VIETNAMESE_LIST_ACTIONS

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get_permitted_actions(self, user, model=None):
        actions = super().get_permitted_actions(user, model=model)
        return filter_access_request_actions_for_user(actions, user, model)

    def get_extra_context(self, request):
        context = AccessRequestExportService.build_control_urls(request)
        return apply_model_label_context(context, AccessRequest)

    def get(self, request):
        if AccessRequestExportService.is_custom_export_request(request):
            if self.filterset:
                self.queryset = self.filterset(request.GET, self.queryset, request=request).qs
            return AccessRequestExportService.dispatch_custom_export(
                request,
                view=self,
                queryset=self.queryset,
            )

        return super().get(request)


class AccessRequestView(ObjectView):
    queryset = AccessRequest.objects.select_related("region", "site").prefetch_related("tags")
    template_name = "netbox_smartlock/accessrequest.html"
    actions = VIETNAMESE_DETAIL_ACTIONS

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get_permitted_actions(self, user, model=None):
        actions = super().get_permitted_actions(user, model=model)
        return filter_access_request_actions_for_user(actions, user, model)

    def get_extra_context(self, request, instance):
        is_admin = is_access_request_admin(request.user)
        can_manage_request = can_manage_access_request(request.user, instance)
        can_manage_persons = can_manage_access_request_persons(request.user)
        persons = annotate_file_count(
            instance.persons.select_related("request", "location").prefetch_related("tags"),
            model_name="accessrequestperson",
        )
        admin_action_person_ids = set()
        if can_manage_persons:
            admin_action_person_ids = set(
                AccessRequestPerson.objects.filter(
                    pk__in=persons.values_list("pk", flat=True)
                )
                .restrict(request.user, "change")
                .values_list("pk", flat=True)
            )
        persons_table = AccessRequestPersonTable(persons)
        persons_table.columns.hide("request")
        if can_manage_persons:
            persons_table.columns.hide("actions")
        persons_table.configure(request)
        content_type = ContentType.objects.get_for_model(instance)
        changelog_entries = (
            ObjectChange.objects.filter(
                changed_object_type=content_type,
                changed_object_id=instance.pk,
            )
            .select_related("user", "changed_object_type")
            .order_by("-time", "-pk")
        )

        return apply_model_label_context({
            "persons": persons,
            "persons_table": persons_table,
            "history_entries": instance.history_entries.select_related("actor"),
            "changelog_entries": changelog_entries,
            "access_request_status_label": label_for(ACCESS_REQUEST_STATUS_LABELS, instance.status),
            "person_verify_labels": ACCESS_REQUEST_PERSON_VERIFY_LABELS,
            "person_access_labels": ACCESS_REQUEST_PERSON_ACCESS_LABELS,
            "is_access_request_admin": is_admin,
            "can_manage_access_request": can_manage_request,
            "can_manage_access_request_persons": can_manage_persons,
            "can_add_access_request_persons": request.user.has_perm("netbox_smartlock.add_accessrequestperson"),
            "can_send_access_request": can_submit_access_request(request.user, instance),
            "admin_action_person_ids": admin_action_person_ids,
        }, instance)


class AccessRequestEditView(AccessRequestAdminCrudGuardMixin, VietnameseModelLabelMixin, ObjectEditView):
    queryset = AccessRequest.objects.all()
    form = AccessRequestForm
    template_name = "netbox_smartlock/object_edit_cancel_confirm.html"

    def dispatch(self, request, *args, **kwargs):
        self.form = request_scoped_form(AccessRequestForm, request_user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk and request.user.is_authenticated:
            obj.created_by = request.user
        return obj

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.pk and not obj.can_guest_edit:
            raise PermissionDenied(ACCESS_REQUEST_GUEST_EDIT_DENIED_MESSAGE)
        return obj


class AccessRequestImportView(AccessRequestAdminCrudGuardMixin, VietnameseModelLabelMixin, BulkImportView):
    queryset = AccessRequest.objects.all()
    model_form = AccessRequestImportForm
    template_name = "netbox_smartlock/bulk_import.html"

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def dispatch(self, request, *args, **kwargs):
        self.model_form = request_scoped_form(AccessRequestImportForm, request_user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def save_object(self, object_form, request):
        if not object_form.instance.pk and request.user.is_authenticated:
            object_form.instance.created_by = request.user
        return super().save_object(object_form, request)


class AccessRequestBulkGuardMixin:
    def get_selected_requests(self, request):
        """Lấy đúng tập phiếu được chọn, bao gồm trường hợp chọn tất cả sau filter."""
        queryset = restrict_access_requests_for_user(self.queryset, request.user)
        if request.POST.get("_all") and self.filterset is not None:
            return self.filterset(request.GET, queryset, request=request).qs
        pk_list = request.POST.getlist("pk")
        return queryset.filter(pk__in=pk_list)

    def enforce_guest_bulk_access(self, request, *, denied_message):
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_ADMIN_CRUD_MESSAGE)
        if self.get_selected_requests(request).filter(
            status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
        ).exists():
            raise PermissionDenied(denied_message)


class AccessRequestBulkEditView(AccessRequestBulkGuardMixin, VietnameseModelLabelMixin, BulkEditView):
    queryset = AccessRequest.objects.all()
    filterset = AccessRequestFilterSet
    table = AccessRequestTable
    form = AccessRequestBulkEditForm
    template_name = "netbox_smartlock/bulk_edit.html"

    def dispatch(self, request, *args, **kwargs):
        self.form = request_scoped_form(AccessRequestBulkEditForm, request_user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_ADMIN_CRUD_MESSAGE)
        return super().get(request)

    def post(self, request, **kwargs):
        self.enforce_guest_bulk_access(
            request,
            denied_message=ACCESS_REQUEST_GUEST_EDIT_DENIED_MESSAGE,
        )
        return super().post(request, **kwargs)


class AccessRequestBulkRenameView(AccessRequestBulkGuardMixin, VietnameseModelLabelMixin, BulkRenameView):
    queryset = AccessRequest.objects.all()
    filterset = AccessRequestFilterSet
    template_name = "netbox_smartlock/bulk_rename.html"

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_ADMIN_CRUD_MESSAGE)
        return super().get(request)

    def post(self, request, **kwargs):
        self.enforce_guest_bulk_access(
            request,
            denied_message=ACCESS_REQUEST_GUEST_EDIT_DENIED_MESSAGE,
        )
        return super().post(request, **kwargs)


class AccessRequestBulkDeleteView(AccessRequestBulkGuardMixin, VietnameseModelLabelMixin, BulkDeleteView):
    queryset = AccessRequest.objects.all()
    filterset = AccessRequestFilterSet
    table = AccessRequestTable
    template_name = "netbox_smartlock/bulk_delete.html"

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_ADMIN_CRUD_MESSAGE)
        return super().get(request)

    def post(self, request, **kwargs):
        self.enforce_guest_bulk_access(
            request,
            denied_message=ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE,
        )
        return super().post(request, **kwargs)


class AccessRequestDeleteView(AccessRequestAdminCrudGuardMixin, VietnameseModelLabelMixin, ObjectDeleteView):
    queryset = AccessRequest.objects.all()
    template_name = "netbox_smartlock/object_delete.html"

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.pk and not obj.can_guest_delete:
            raise PermissionDenied(ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE)
        return obj


class AccessRequestChangeLogView(ScopedObjectChangeLogView):
    queryset = AccessRequest.objects.all()

    def get_parent_queryset(self, request, model):
        return restrict_access_requests_for_user(super().get_parent_queryset(request, model), request.user)


class AccessRequestSendView(ObjectView):
    queryset = AccessRequest.objects.select_related("region", "site").prefetch_related("tags")

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def post(self, request, **kwargs):
        instance = self.get_object(**kwargs)
        if not can_submit_access_request(request.user, instance):
            raise PermissionDenied(ACCESS_REQUEST_SEND_PERMISSION_MESSAGE)

        try:
            instance.submit(user=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, f"Đã gửi phiếu yêu cầu {instance}.")
        return redirect(instance.get_absolute_url())


class AccessRequestWorkflowView(ObjectView):
    queryset = AccessRequest.objects.select_related("region", "site").prefetch_related("tags")
    action = None
    success_message = ""

    def post(self, request, **kwargs):
        if not can_manage_access_requests(request.user):
            raise PermissionDenied(ACCESS_REQUEST_WORKFLOW_PERMISSION_MESSAGE)

        instance = self.get_object(**kwargs)
        if not can_manage_access_request(request.user, instance):
            raise PermissionDenied(ACCESS_REQUEST_OBJECT_WORKFLOW_PERMISSION_MESSAGE)

        description = request.POST.get("description", "")
        try:
            getattr(instance, self.action)(user=request.user, description=description)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, self.success_message.format(instance=instance))
        return redirect(instance.get_absolute_url())


class AccessRequestConfirmView(AccessRequestWorkflowView):
    action = "confirm"
    success_message = "Đã xác nhận phiếu yêu cầu {instance}."


class AccessRequestAcceptView(AccessRequestWorkflowView):
    action = "accept"
    success_message = "Đã chấp nhận phiếu yêu cầu {instance}."


class AccessRequestRejectView(AccessRequestWorkflowView):
    action = "reject"
    success_message = "Đã từ chối phiếu yêu cầu {instance}."


class AccessRequestCompleteView(AccessRequestWorkflowView):
    action = "complete"
    success_message = "Đã hoàn thành phiếu yêu cầu {instance}."


class AccessRequestPersonListView(ObjectListView):
    queryset = annotate_file_count(
        AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags"),
        model_name="accessrequestperson",
    )
    table = AccessRequestPersonTable
    filterset = AccessRequestPersonFilterSet
    filterset_form = AccessRequestPersonFilterForm
    template_name = "netbox_smartlock/object_list.html"
    actions = VIETNAMESE_LIST_ACTIONS_WITHOUT_RENAME

    def get_extra_context(self, request):
        return apply_model_label_context({}, AccessRequestPerson)

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get_permitted_actions(self, user, model=None):
        actions = super().get_permitted_actions(user, model=model)
        return filter_access_request_actions_for_user(actions, user, model)


class AccessRequestPersonImportView(VietnameseModelLabelMixin, BulkImportView):
    queryset = AccessRequestPerson.objects.all()
    model_form = AccessRequestPersonImportForm
    template_name = "netbox_smartlock/bulk_import.html"

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def dispatch(self, request, *args, **kwargs):
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE)
        scoped_request_id_value = request.GET.get("request") or request.POST.get("request")
        self.model_form = request_scoped_form(
            AccessRequestPersonImportForm,
            request_user=request.user,
            scoped_request_id=scoped_request_id_value,
        )
        return super().dispatch(request, *args, **kwargs)


class AccessRequestPersonBulkGuardMixin:
    def get_selected_persons(self, request):
        """Lấy đúng tập đối tượng được chọn trong scope nhìn thấy của user."""
        queryset = restrict_access_request_persons_for_user(self.queryset, request.user)
        if request.POST.get("_all") and self.filterset is not None:
            return self.filterset(request.GET, queryset, request=request).qs
        pk_list = request.POST.getlist("pk")
        return queryset.filter(pk__in=pk_list)

    def enforce_guest_person_bulk_edit_access(self, request):
        """Bulk edit chỉ được phép khi mọi đối tượng còn sửa được theo workflow Guest."""
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE)
        selected = self.get_selected_persons(request)
        has_locked_verify_status = selected.exclude(
            verify_status__in=(AccessRequestPerson.VERIFY_PENDING, AccessRequestPerson.VERIFY_INVALID)
        ).exclude(
            request__status=AccessRequest.STATUS_REJECTED
        ).exists()
        has_locked_request_status = selected.filter(
            request__status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
        ).exists()
        if has_locked_verify_status or has_locked_request_status:
            raise PermissionDenied(ACCESS_REQUEST_PERSON_EDIT_DENIED_MESSAGE)

    def enforce_guest_person_bulk_delete_access(self, request):
        """Bulk delete cho phép xóa sau accepted/rejected nhưng chặn completed."""
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE)
        selected = self.get_selected_persons(request)
        has_locked_verify_status = selected.exclude(
            verify_status__in=(AccessRequestPerson.VERIFY_PENDING, AccessRequestPerson.VERIFY_INVALID)
        ).exclude(
            request__status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_REJECTED)
        ).exists()
        has_completed_request = selected.filter(request__status=AccessRequest.STATUS_COMPLETED).exists()
        if has_locked_verify_status or has_completed_request:
            raise PermissionDenied(ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE)


class AccessRequestPersonBulkEditView(AccessRequestPersonBulkGuardMixin, VietnameseModelLabelMixin, BulkEditView):
    queryset = AccessRequestPerson.objects.all()
    filterset = AccessRequestPersonFilterSet
    table = AccessRequestPersonTable
    form = AccessRequestPersonBulkEditForm
    template_name = "netbox_smartlock/bulk_edit.html"

    def dispatch(self, request, *args, **kwargs):
        selected_persons_queryset_value = None
        if request.method == "POST":
            selected_persons_queryset_value = self.get_selected_persons(request)

        self.form = request_scoped_form(
            AccessRequestPersonBulkEditForm,
            request_user=request.user,
            selected_persons_queryset=selected_persons_queryset_value,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE)
        return super().get(request)

    def post(self, request, **kwargs):
        self.enforce_guest_person_bulk_edit_access(request)
        return super().post(request, **kwargs)


class AccessRequestPersonBulkDeleteView(AccessRequestPersonBulkGuardMixin, VietnameseModelLabelMixin, BulkDeleteView):
    queryset = AccessRequestPerson.objects.all()
    filterset = AccessRequestPersonFilterSet
    table = AccessRequestPersonTable
    template_name = "netbox_smartlock/bulk_delete.html"

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        enforce_guest_crud_access(request.user, ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE)
        return super().get(request)

    def post(self, request, **kwargs):
        self.enforce_guest_person_bulk_delete_access(request)
        return super().post(request, **kwargs)


class AccessRequestPersonView(ObjectView):
    queryset = AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags")
    template_name = "netbox_smartlock/accessrequestperson.html"
    actions = VIETNAMESE_DETAIL_ACTIONS

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get_permitted_actions(self, user, model=None):
        actions = super().get_permitted_actions(user, model=model)
        return filter_access_request_actions_for_user(actions, user, model)

    def get_extra_context(self, request, instance):
        return apply_model_label_context({
            "uploaded_files": files_for_object(instance, model_name="accessrequestperson"),
            "is_access_request_admin": is_access_request_admin(request.user),
            "can_manage_access_request_persons": can_manage_access_request_person(request.user, instance),
        }, instance)


class AccessRequestPersonEditView(AccessRequestAdminCrudGuardMixin, VietnameseModelLabelMixin, ObjectEditView):
    queryset = AccessRequestPerson.objects.all()
    form = AccessRequestPersonForm
    template_name = "netbox_smartlock/object_edit_cancel_confirm.html"
    admin_crud_message = ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE

    def dispatch(self, request, *args, **kwargs):
        self.form = request_scoped_form(AccessRequestPersonForm, request_user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk and request.GET.get("request"):
            obj.request_id = request.GET.get("request")
        return obj

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.pk and not obj.can_guest_edit:
            raise PermissionDenied(ACCESS_REQUEST_PERSON_EDIT_DENIED_MESSAGE)
        return obj


class AccessRequestPersonDeleteView(AccessRequestAdminCrudGuardMixin, VietnameseModelLabelMixin, ObjectDeleteView):
    queryset = AccessRequestPerson.objects.all()
    admin_crud_message = ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE
    template_name = "netbox_smartlock/object_delete.html"

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.pk and not obj.can_guest_delete:
            raise PermissionDenied(ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE)
        return obj


class AccessRequestPersonChangeLogView(ScopedObjectChangeLogView):
    queryset = AccessRequestPerson.objects.all()

    def get_parent_queryset(self, request, model):
        return restrict_access_request_persons_for_user(super().get_parent_queryset(request, model), request.user)


class AccessRequestPersonWorkflowView(ObjectView):
    queryset = AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags")
    action = None
    success_message = ""

    def post(self, request, **kwargs):
        if not can_manage_access_request_persons(request.user):
            raise PermissionDenied(ACCESS_REQUEST_PERSON_WORKFLOW_PERMISSION_MESSAGE)

        person = self.get_object(**kwargs)
        if not can_manage_access_request_person(request.user, person):
            raise PermissionDenied(ACCESS_REQUEST_PERSON_OBJECT_WORKFLOW_PERMISSION_MESSAGE)

        description = request.POST.get("description", "")
        try:
            getattr(person, self.action)(user=request.user, description=description)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, self.success_message.format(person=person))
        return redirect(request.POST.get("return_url") or person.request.get_absolute_url())


class AccessRequestPersonVerifyValidView(AccessRequestPersonWorkflowView):
    action = "mark_valid"
    success_message = "Đã đánh dấu {person} là hợp lệ."


class AccessRequestPersonVerifyInvalidView(AccessRequestPersonWorkflowView):
    action = "mark_invalid"
    success_message = "Đã đánh dấu {person} là không hợp lệ."


class AccessRequestPersonInView(AccessRequestPersonWorkflowView):
    action = "mark_in"
    success_message = "Đã chuyển {person} từ Out sang In."


class AccessRequestPersonOutView(AccessRequestPersonWorkflowView):
    action = "mark_out"
    success_message = "Đã chuyển {person} từ In sang Out."
