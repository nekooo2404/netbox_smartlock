from netbox.api.viewsets import NetBoxModelViewSet
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import AccessRequest, AccessRequestPerson, AssetGroup, SmartLock
from ..filtersets import AccessRequestFilterSet, AccessRequestPersonFilterSet, AssetGroupFilterSet, SmartLockFilterSet
from ..permissions import (
    can_manage_access_request_persons,
    can_manage_access_requests,
    is_access_request_admin,
    restrict_access_request_persons_for_user,
    restrict_access_requests_for_user,
)
from .serializers import AccessRequestPersonSerializer, AccessRequestSerializer, AssetGroupSerializer, SmartLockSerializer


def _raise_drf_validation_error(exc):
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)
    raise serializers.ValidationError(exc.messages)


class AccessRequestAdminActionMixin:
    admin_permission_checker = staticmethod(can_manage_access_requests)
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
            raise PermissionDenied("Only Admin users with NetBox change permission can perform this access request action.")

    def run_workflow_action(self, instance, action_name):
        self.require_access_request_admin()
        description = self.request.data.get("description", "")
        try:
            getattr(instance, action_name)(user=self.request.user, description=description)
        except DjangoValidationError as exc:
            _raise_drf_validation_error(exc)
        instance.refresh_from_db()
        return Response(self.get_serializer(instance).data)


class AccessRequestViewSet(AccessRequestAdminActionMixin, NetBoxModelViewSet):
    workflow_actions = ("confirm", "accept", "reject", "complete")
    queryset = AccessRequest.objects.select_related("region", "site").prefetch_related("tags")
    serializer_class = AccessRequestSerializer
    filterset_class = AccessRequestFilterSet

    def create(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        return super().partial_update(request, *args, **kwargs)

    def get_queryset(self):
        return restrict_access_requests_for_user(super().get_queryset(), self.request.user)

    def perform_create(self, serializer):
        if is_access_request_admin(self.request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        if not serializer.instance and self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
            self._validate_objects(serializer.instance)
            return
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        if is_access_request_admin(self.request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        if is_access_request_admin(self.request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request CRUD.")
        if not instance.can_guest_delete:
            raise PermissionDenied("Accepted or completed access requests cannot be deleted.")
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


class AccessRequestPersonViewSet(AccessRequestAdminActionMixin, NetBoxModelViewSet):
    admin_permission_checker = staticmethod(can_manage_access_request_persons)
    workflow_actions = ("verify_valid", "verify_invalid", "check_in", "check_out")
    queryset = AccessRequestPerson.objects.select_related("request", "location").prefetch_related("tags")
    serializer_class = AccessRequestPersonSerializer
    filterset_class = AccessRequestPersonFilterSet

    def create(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if is_access_request_admin(request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        return super().partial_update(request, *args, **kwargs)

    def get_queryset(self):
        return restrict_access_request_persons_for_user(super().get_queryset(), self.request.user)

    def perform_create(self, serializer):
        if is_access_request_admin(self.request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        if is_access_request_admin(self.request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        if is_access_request_admin(self.request.user):
            raise PermissionDenied("Admin users must use workflow actions instead of generic access request person CRUD.")
        if not instance.can_guest_delete:
            raise PermissionDenied("This access request person cannot be deleted in the current workflow state.")
        return super().perform_destroy(instance)

    @action(detail=True, methods=["post"], url_path="verify-valid")
    def verify_valid(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "mark_valid")

    @action(detail=True, methods=["post"], url_path="verify-invalid")
    def verify_invalid(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "mark_invalid")

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "check_in")

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        self.require_access_request_admin()
        return self.run_workflow_action(self.get_object(), "check_out")


class AssetGroupViewSet(NetBoxModelViewSet):
    queryset = AssetGroup.objects.prefetch_related("tags")
    serializer_class = AssetGroupSerializer
    filterset_class = AssetGroupFilterSet


class SmartLockViewSet(NetBoxModelViewSet):
    queryset = SmartLock.objects.select_related(
        "asset_group", "region", "site", "location", "rack"
    ).prefetch_related("tags")
    serializer_class = SmartLockSerializer
    filterset_class = SmartLockFilterSet
