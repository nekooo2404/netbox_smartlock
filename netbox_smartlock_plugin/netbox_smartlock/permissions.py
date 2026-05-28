from django.db.models import Q


def is_access_request_admin(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or user.groups.filter(name="Admin").exists()
        )
    )


def can_manage_access_requests(user):
    return bool(
        is_access_request_admin(user)
        and user.has_perm("netbox_smartlock.change_accessrequest")
    )


def can_manage_access_request_persons(user):
    return bool(
        is_access_request_admin(user)
        and user.has_perm("netbox_smartlock.change_accessrequestperson")
    )


def can_manage_access_request(user, access_request):
    return bool(
        access_request is not None
        and can_manage_access_requests(user)
        and user.has_perm("netbox_smartlock.change_accessrequest", access_request)
    )


def can_manage_access_request_person(user, access_request_person):
    return bool(
        access_request_person is not None
        and can_manage_access_request_persons(user)
        and user.has_perm("netbox_smartlock.change_accessrequestperson", access_request_person)
    )


def can_submit_access_request(user, access_request):
    return bool(
        access_request is not None
        and not is_access_request_admin(user)
        and user_can_access_request(user, access_request)
        and user.has_perm("netbox_smartlock.change_accessrequest", access_request)
    )


def access_request_scope_q(user):
    if is_access_request_admin(user):
        return Q()
    if not user or not user.is_authenticated:
        return Q(pk__in=[])
    return Q(created_by=user)


def user_can_access_request(user, access_request):
    if is_access_request_admin(user):
        return True
    if not user or not user.is_authenticated or access_request is None:
        return False
    return access_request.created_by_id == user.pk


def restrict_access_requests_for_user(queryset, user):
    if is_access_request_admin(user):
        return queryset
    if not user or not user.is_authenticated:
        return queryset.none()
    return queryset.filter(access_request_scope_q(user))


def restrict_access_request_persons_for_user(queryset, user):
    if is_access_request_admin(user):
        return queryset
    if not user or not user.is_authenticated:
        return queryset.none()
    return queryset.filter(request__created_by=user)
