from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import redirect

from core.choices import ObjectChangeActionChoices
from core.models.change_logging import ObjectChange
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
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkImport, BulkRename, CloneObject, DeleteObject, EditObject

from .change_logging import annotate_creator
from .contracts import SMARTLOCK_IMPORT_CSV_DESCRIPTION, SMARTLOCK_IMPORT_HELP_ITEMS
from .exports import AccessRequestExportService, SmartLockExportService
from .filtersets import AccessRequestFilterSet, AccessRequestPersonFilterSet, AssetGroupFilterSet, SmartLockFilterSet
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
    SmartLockFilterForm,
    SmartLockForm,
    SmartLockImportForm,
)
from .mapping import format_rack_lookup, get_warranty_state
from .models import AccessRequest, AccessRequestPerson, AssetGroup, SmartLock
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
from .tables import AccessRequestPersonTable, AccessRequestTable, AssetGroupTable, SmartLockTable
from .upload_files import annotate_file_count, files_for_object


def filter_guest_object_actions(actions, instance):
    filtered_actions = []
    for action in actions:
        if action is EditObject and not getattr(instance, "can_guest_edit", True):
            continue
        if action is DeleteObject and not getattr(instance, "can_guest_delete", True):
            continue
        filtered_actions.append(action)
    return tuple(filtered_actions)


def filter_access_request_actions_for_user(actions, user, instance_or_model=None):
    if not is_access_request_admin(user):
        if instance_or_model is not None and not isinstance(instance_or_model, type):
            return filter_guest_object_actions(actions, instance_or_model)
        return actions

    blocked_actions = {AddObject, BulkImport, BulkEdit, BulkRename, BulkDelete, CloneObject, EditObject, DeleteObject}
    return tuple(action for action in actions if action not in blocked_actions)


class AccessRequestAdminCrudGuardMixin:
    admin_crud_message = "Admin users must use workflow actions instead of generic access request CRUD."

    def dispatch(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied(self.admin_crud_message)
        return super().dispatch(request, *args, **kwargs)


class AssetGroupListView(ObjectListView):
    queryset = annotate_file_count(
        AssetGroup.objects.prefetch_related("tags"),
        model_name="assetgroup",
    )
    table = AssetGroupTable
    filterset = AssetGroupFilterSet
    filterset_form = AssetGroupFilterForm


class AssetGroupView(ObjectView):
    queryset = AssetGroup.objects.prefetch_related("tags")

    def get_extra_context(self, request, instance):
        smartlocks = instance.smartlocks.select_related("site", "location", "rack").prefetch_related("tags")
        return {
            "smartlocks": smartlocks,
            "uploaded_files": files_for_object(instance, model_name="assetgroup"),
        }


class AssetGroupEditView(ObjectEditView):
    queryset = AssetGroup.objects.all()
    form = AssetGroupForm


class AssetGroupImportView(BulkImportView):
    queryset = AssetGroup.objects.all()
    model_form = AssetGroupImportForm


class AssetGroupDeleteView(ObjectDeleteView):
    queryset = AssetGroup.objects.all()


class AssetGroupChangeLogView(ObjectChangeLogView):
    queryset = AssetGroup.objects.all()


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

    def get_extra_context(self, request):
        return SmartLockExportService.build_control_urls(request)

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

    def get_extra_context(self, request, instance):
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
        return {
            "uploaded_files": files_for_object(instance, model_name="smartlock"),
            "rack_lookup": format_rack_lookup(instance.rack),
            "warranty_state": get_warranty_state(instance.warranty_expiration_date),
            "created_by_name": creator or "-",
        }


class SmartLockEditView(ObjectEditView):
    queryset = SmartLock.objects.all()
    form = SmartLockForm

    def dispatch(self, request, *args, **kwargs):
        class RequestScopedSmartLockForm(SmartLockForm):
            request_user = request.user

        self.form = RequestScopedSmartLockForm
        return super().dispatch(request, *args, **kwargs)


class SmartLockImportView(BulkImportView):
    queryset = SmartLock.objects.all()
    model_form = SmartLockImportForm

    def dispatch(self, request, *args, **kwargs):
        class RequestScopedSmartLockImportForm(SmartLockImportForm):
            request_user = request.user

        self.model_form = RequestScopedSmartLockImportForm
        return super().dispatch(request, *args, **kwargs)

    def get_extra_context(self, request):
        return {
            "csv_description": SMARTLOCK_IMPORT_CSV_DESCRIPTION,
            "csv_help_items": SMARTLOCK_IMPORT_HELP_ITEMS,
        }


class SmartLockDeleteView(ObjectDeleteView):
    queryset = SmartLock.objects.all()


class SmartLockChangeLogView(ObjectChangeLogView):
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

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get_permitted_actions(self, user, model=None):
        actions = super().get_permitted_actions(user, model=model)
        return filter_access_request_actions_for_user(actions, user, model)

    def get_extra_context(self, request):
        return AccessRequestExportService.build_control_urls(request)

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

        return {
            "persons": persons,
            "persons_table": persons_table,
            "history_entries": instance.history_entries.select_related("actor"),
            "changelog_entries": changelog_entries,
            "is_access_request_admin": is_admin,
            "can_manage_access_request": can_manage_request,
            "can_manage_access_request_persons": can_manage_persons,
            "can_add_access_request_persons": request.user.has_perm("netbox_smartlock.add_accessrequestperson"),
            "can_send_access_request": can_submit_access_request(request.user, instance),
            "admin_action_person_ids": admin_action_person_ids,
        }


class AccessRequestEditView(AccessRequestAdminCrudGuardMixin, ObjectEditView):
    queryset = AccessRequest.objects.all()
    form = AccessRequestForm
    template_name = "netbox_smartlock/object_edit_cancel_confirm.html"

    def dispatch(self, request, *args, **kwargs):
        class RequestScopedAccessRequestForm(AccessRequestForm):
            request_user = request.user

        self.form = RequestScopedAccessRequestForm
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
            raise PermissionDenied("Accepted or completed access requests cannot be edited by a guest user.")
        return obj


class AccessRequestImportView(AccessRequestAdminCrudGuardMixin, BulkImportView):
    queryset = AccessRequest.objects.all()
    model_form = AccessRequestImportForm

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def dispatch(self, request, *args, **kwargs):
        class RequestScopedAccessRequestImportForm(AccessRequestImportForm):
            request_user = request.user

        self.model_form = RequestScopedAccessRequestImportForm
        return super().dispatch(request, *args, **kwargs)

    def save_object(self, object_form, request):
        if not object_form.instance.pk and request.user.is_authenticated:
            object_form.instance.created_by = request.user
        return super().save_object(object_form, request)


class AccessRequestBulkGuardMixin:
    def get_selected_requests(self, request):
        queryset = restrict_access_requests_for_user(self.queryset, request.user)
        if request.POST.get("_all") and self.filterset is not None:
            return self.filterset(request.GET, queryset, request=request).qs
        pk_list = request.POST.getlist("pk")
        return queryset.filter(pk__in=pk_list)


class AccessRequestBulkEditView(AccessRequestBulkGuardMixin, BulkEditView):
    queryset = AccessRequest.objects.all()
    filterset = AccessRequestFilterSet
    table = AccessRequestTable
    form = AccessRequestBulkEditForm

    def dispatch(self, request, *args, **kwargs):
        class RequestScopedAccessRequestBulkEditForm(AccessRequestBulkEditForm):
            request_user = request.user

        self.form = RequestScopedAccessRequestBulkEditForm
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        return super().get(request)

    def post(self, request, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        if self.get_selected_requests(request).filter(
            status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
        ).exists():
            raise PermissionDenied("Accepted or completed access requests cannot be edited by a guest user.")
        return super().post(request, **kwargs)


class AccessRequestBulkRenameView(AccessRequestBulkGuardMixin, BulkRenameView):
    queryset = AccessRequest.objects.all()
    filterset = AccessRequestFilterSet

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        return super().get(request)

    def post(self, request, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        if self.get_selected_requests(request).filter(
            status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
        ).exists():
            raise PermissionDenied("Accepted or completed access requests cannot be edited by a guest user.")
        return super().post(request, **kwargs)


class AccessRequestBulkDeleteView(AccessRequestBulkGuardMixin, BulkDeleteView):
    queryset = AccessRequest.objects.all()
    filterset = AccessRequestFilterSet
    table = AccessRequestTable

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        return super().get(request)

    def post(self, request, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        if self.get_selected_requests(request).filter(
            status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
        ).exists():
            raise PermissionDenied("Accepted or completed access requests cannot be deleted by a guest user.")
        return super().post(request, **kwargs)


class AccessRequestDeleteView(AccessRequestAdminCrudGuardMixin, ObjectDeleteView):
    queryset = AccessRequest.objects.all()

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.pk and not obj.can_guest_delete:
            raise PermissionDenied("Accepted or completed access requests cannot be deleted by a guest user.")
        return obj


class AccessRequestChangeLogView(ObjectChangeLogView):
    queryset = AccessRequest.objects.all()

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)


class AccessRequestSendView(ObjectView):
    queryset = AccessRequest.objects.select_related("region", "site").prefetch_related("tags")

    def get_queryset(self, request):
        return restrict_access_requests_for_user(super().get_queryset(request), request.user)

    def post(self, request, **kwargs):
        instance = self.get_object(**kwargs)
        if not can_submit_access_request(request.user, instance):
            raise PermissionDenied("Only the request creator with NetBox change permission can submit this access request.")

        try:
            instance.submit(user=request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, f"Submitted access request {instance}.")
        return redirect(instance.get_absolute_url())


class AccessRequestWorkflowView(ObjectView):
    queryset = AccessRequest.objects.select_related("region", "site").prefetch_related("tags")
    action = None
    success_message = ""

    def post(self, request, **kwargs):
        if not can_manage_access_requests(request.user):
            raise PermissionDenied("Only Admin users with NetBox change permission can perform this access request action.")

        instance = self.get_object(**kwargs)
        if not can_manage_access_request(request.user, instance):
            raise PermissionDenied("Only Admin users with NetBox change permission for this object can perform this access request action.")

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
    success_message = "Confirmed access request {instance}."


class AccessRequestAcceptView(AccessRequestWorkflowView):
    action = "accept"
    success_message = "Accepted access request {instance}."


class AccessRequestRejectView(AccessRequestWorkflowView):
    action = "reject"
    success_message = "Rejected access request {instance}."


class AccessRequestCompleteView(AccessRequestWorkflowView):
    action = "complete"
    success_message = "Completed access request {instance}."


class AccessRequestPersonListView(ObjectListView):
    queryset = annotate_file_count(
        AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags"),
        model_name="accessrequestperson",
    )
    table = AccessRequestPersonTable
    filterset = AccessRequestPersonFilterSet
    filterset_form = AccessRequestPersonFilterForm

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get_permitted_actions(self, user, model=None):
        actions = super().get_permitted_actions(user, model=model)
        return filter_access_request_actions_for_user(actions, user, model)


class AccessRequestPersonImportView(BulkImportView):
    queryset = AccessRequestPerson.objects.all()
    model_form = AccessRequestPersonImportForm

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def dispatch(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        scoped_request_id_value = request.GET.get("request") or request.POST.get("request")

        class RequestScopedAccessRequestPersonImportForm(AccessRequestPersonImportForm):
            request_user = request.user
            scoped_request_id = scoped_request_id_value

        self.model_form = RequestScopedAccessRequestPersonImportForm
        return super().dispatch(request, *args, **kwargs)


class AccessRequestPersonBulkGuardMixin:
    def get_selected_persons(self, request):
        queryset = restrict_access_request_persons_for_user(self.queryset, request.user)
        if request.POST.get("_all") and self.filterset is not None:
            return self.filterset(request.GET, queryset, request=request).qs
        pk_list = request.POST.getlist("pk")
        return queryset.filter(pk__in=pk_list)


class AccessRequestPersonBulkEditView(AccessRequestPersonBulkGuardMixin, BulkEditView):
    queryset = AccessRequestPerson.objects.all()
    filterset = AccessRequestPersonFilterSet
    table = AccessRequestPersonTable
    form = AccessRequestPersonBulkEditForm

    def dispatch(self, request, *args, **kwargs):
        selected_persons_queryset_value = None
        if request.method == "POST":
            selected_persons_queryset_value = self.get_selected_persons(request)

        class RequestScopedAccessRequestPersonBulkEditForm(AccessRequestPersonBulkEditForm):
            request_user = request.user
            selected_persons_queryset = selected_persons_queryset_value

        self.form = RequestScopedAccessRequestPersonBulkEditForm
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        return super().get(request)

    def post(self, request, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        selected = self.get_selected_persons(request)
        if selected.exclude(
            verify_status__in=(AccessRequestPerson.VERIFY_PENDING, AccessRequestPerson.VERIFY_INVALID)
        ).exclude(
            request__status=AccessRequest.STATUS_REJECTED
        ).exists() or selected.filter(
            request__status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_COMPLETED)
        ).exists():
            raise PermissionDenied("These access request persons cannot be edited in the current workflow state.")
        return super().post(request, **kwargs)


class AccessRequestPersonBulkDeleteView(AccessRequestPersonBulkGuardMixin, BulkDeleteView):
    queryset = AccessRequestPerson.objects.all()
    filterset = AccessRequestPersonFilterSet
    table = AccessRequestPersonTable

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get(self, request):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        return super().get(request)

    def post(self, request, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        selected = self.get_selected_persons(request)
        if selected.exclude(
            verify_status__in=(AccessRequestPerson.VERIFY_PENDING, AccessRequestPerson.VERIFY_INVALID)
        ).exclude(
            request__status__in=(AccessRequest.STATUS_ACCEPTED, AccessRequest.STATUS_REJECTED)
        ).exists() or selected.filter(
            request__status=AccessRequest.STATUS_COMPLETED
        ).exists():
            raise PermissionDenied("These access request persons cannot be deleted in the current workflow state.")
        return super().post(request, **kwargs)


class AccessRequestPersonView(ObjectView):
    queryset = AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags")
    template_name = "netbox_smartlock/accessrequestperson.html"

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get_permitted_actions(self, user, model=None):
        actions = super().get_permitted_actions(user, model=model)
        return filter_access_request_actions_for_user(actions, user, model)

    def get_extra_context(self, request, instance):
        return {
            "uploaded_files": files_for_object(instance, model_name="accessrequestperson"),
            "is_access_request_admin": is_access_request_admin(request.user),
            "can_manage_access_request_persons": can_manage_access_request_person(request.user, instance),
        }


class AccessRequestPersonEditView(AccessRequestAdminCrudGuardMixin, ObjectEditView):
    queryset = AccessRequestPerson.objects.all()
    form = AccessRequestPersonForm
    template_name = "netbox_smartlock/object_edit_cancel_confirm.html"
    admin_crud_message = "Admin users must use workflow actions instead of generic access request person CRUD."

    def dispatch(self, request, *args, **kwargs):
        class RequestScopedAccessRequestPersonForm(AccessRequestPersonForm):
            request_user = request.user

        self.form = RequestScopedAccessRequestPersonForm
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
            raise PermissionDenied("This access request person cannot be edited in the current workflow state.")
        return obj


class AccessRequestPersonDeleteView(AccessRequestAdminCrudGuardMixin, ObjectDeleteView):
    queryset = AccessRequestPerson.objects.all()
    admin_crud_message = "Admin users must use workflow actions instead of generic access request person CRUD."

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        if obj.pk and not obj.can_guest_delete:
            raise PermissionDenied("This access request person cannot be deleted in the current workflow state.")
        return obj


class AccessRequestPersonChangeLogView(ObjectChangeLogView):
    queryset = AccessRequestPerson.objects.all()

    def get_queryset(self, request):
        return restrict_access_request_persons_for_user(super().get_queryset(request), request.user)


class AccessRequestPersonWorkflowView(ObjectView):
    queryset = AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags")
    action = None
    success_message = ""

    def post(self, request, **kwargs):
        if not can_manage_access_request_persons(request.user):
            raise PermissionDenied("Only Admin users with NetBox change permission can perform this access request person action.")

        person = self.get_object(**kwargs)
        if not can_manage_access_request_person(request.user, person):
            raise PermissionDenied("Only Admin users with NetBox change permission for this object can perform this access request person action.")

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
    success_message = "Marked {person} as valid."


class AccessRequestPersonVerifyInvalidView(AccessRequestPersonWorkflowView):
    action = "mark_invalid"
    success_message = "Marked {person} as invalid."


class AccessRequestPersonCheckInView(AccessRequestPersonWorkflowView):
    action = "check_in"
    success_message = "Checked in {person}."


class AccessRequestPersonCheckOutView(AccessRequestPersonWorkflowView):
    action = "check_out"
    success_message = "Checked out {person}."
