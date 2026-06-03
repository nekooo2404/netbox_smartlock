from netbox.api.viewsets import NetBoxModelViewSet
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock
from ..filtersets import (
    AccessRequestFilterSet,
    AccessRequestPersonFilterSet,
    AssetGroupFilterSet,
    DeviceAssetFilterSet,
    SmartLockFilterSet,
)
from ..messages import (
    ACCESS_REQUEST_ADMIN_CRUD_MESSAGE,
    ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE,
    ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE,
    ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE,
    ACCESS_REQUEST_PERSON_WORKFLOW_PERMISSION_MESSAGE,
    ACCESS_REQUEST_WORKFLOW_PERMISSION_MESSAGE,
)
from ..permissions import (
    can_manage_access_request_persons,
    can_manage_access_requests,
    is_access_request_admin,
    restrict_access_request_persons_for_user,
    restrict_access_requests_for_user,
)
from .errors import raise_serializer_validation_error
from .serializers import (
    AccessRequestPersonSerializer,
    AccessRequestSerializer,
    AssetGroupSerializer,
    AssetSerializer,
    SmartLockSerializer,
)


class AdminCrudGuardMixin:
    """Chặn Admin dùng CRUD API thường cho các model phải đi qua workflow nghiệp vụ."""

    admin_crud_message = ""

    def enforce_guest_crud_access(self):
        if is_access_request_admin(self.request.user):
            raise PermissionDenied(self.admin_crud_message)

    def create(self, request, *args, **kwargs):
        self.enforce_guest_crud_access()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.enforce_guest_crud_access()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.enforce_guest_crud_access()
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        self.enforce_guest_crud_access()
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        self.enforce_guest_crud_access()
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        self.enforce_guest_crud_access()
        return super().perform_destroy(instance)


class AccessRequestAdminActionMixin:
    """Mở quyền POST workflow, sau đó scope queryset theo quyền change object của NetBox."""

    admin_permission_checker = staticmethod(can_manage_access_requests)
    workflow_permission_message = ACCESS_REQUEST_WORKFLOW_PERMISSION_MESSAGE
    workflow_actions = ()

    def is_workflow_action(self):
        return self.request.method.lower() == "post" and getattr(self, "action", None) in self.workflow_actions

    def get_permissions(self):
        if self.is_workflow_action():
            return [IsAuthenticated()]
        return super().get_permissions()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.is_workflow_action():
            self.queryset = self.__class__.queryset.all().restrict(request.user, "change")

    def require_access_request_admin(self):
        if not self.admin_permission_checker(self.request.user):
            raise PermissionDenied(self.workflow_permission_message)

    def run_workflow_action(self, instance, action_name):
        self.require_access_request_admin()
        description = self.request.data.get("description", "")
        try:
            getattr(instance, action_name)(user=self.request.user, description=description)
        except DjangoValidationError as exc:
            raise_serializer_validation_error(exc)
        instance.refresh_from_db()
        return Response(self.get_serializer(instance).data)


class AccessRequestViewSet(AdminCrudGuardMixin, AccessRequestAdminActionMixin, NetBoxModelViewSet):
    admin_crud_message = ACCESS_REQUEST_ADMIN_CRUD_MESSAGE
    workflow_actions = ("confirm", "accept", "reject", "complete")
    queryset = AccessRequest.objects.select_related("region", "site").prefetch_related("tags")
    serializer_class = AccessRequestSerializer
    filterset_class = AccessRequestFilterSet

    def get_queryset(self):
        return restrict_access_requests_for_user(super().get_queryset(), self.request.user)

    def perform_create(self, serializer):
        self.enforce_guest_crud_access()
        if not serializer.instance and self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
            self._validate_objects(serializer.instance)
            return
        return super().perform_create(serializer)

    def perform_destroy(self, instance):
        self.enforce_guest_crud_access()
        if not instance.can_guest_delete:
            raise PermissionDenied(ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE)
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "confirm")

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "accept")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "reject")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "complete")


class AccessRequestPersonViewSet(AdminCrudGuardMixin, AccessRequestAdminActionMixin, NetBoxModelViewSet):
    admin_crud_message = ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE
    admin_permission_checker = staticmethod(can_manage_access_request_persons)
    workflow_permission_message = ACCESS_REQUEST_PERSON_WORKFLOW_PERMISSION_MESSAGE
    workflow_actions = ("verify_valid", "verify_invalid", "in_", "out")
    queryset = AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags")
    serializer_class = AccessRequestPersonSerializer
    filterset_class = AccessRequestPersonFilterSet

    def get_queryset(self):
        return restrict_access_request_persons_for_user(super().get_queryset(), self.request.user)

    def perform_destroy(self, instance):
        self.enforce_guest_crud_access()
        if not instance.can_guest_delete:
            raise PermissionDenied(ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE)
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="verify-valid")
    def verify_valid(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "mark_valid")

    @action(detail=True, methods=["post"], url_path="verify-invalid")
    def verify_invalid(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "mark_invalid")

    @action(detail=True, methods=["post"], url_path="in", url_name="in")
    def in_(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "mark_in")

    @action(detail=True, methods=["post"], url_path="out")
    def out(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "mark_out")


class AssetGroupViewSet(NetBoxModelViewSet):
    queryset = AssetGroup.objects.prefetch_related("tags")
    serializer_class = AssetGroupSerializer
    filterset_class = AssetGroupFilterSet


class AssetViewSet(NetBoxModelViewSet):
    queryset = Asset.objects.select_related(
        "asset_group", "device", "device__device_type__manufacturer",
        "device__site", "device__location", "device__rack",
    ).prefetch_related("tags")
    serializer_class = AssetSerializer
    filterset_class = DeviceAssetFilterSet


class SmartLockViewSet(NetBoxModelViewSet):
    queryset = SmartLock.objects.select_related(
        "asset_group", "region", "site", "location", "rack"
    ).prefetch_related("tags")
    serializer_class = SmartLockSerializer
    filterset_class = SmartLockFilterSet
