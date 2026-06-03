from django.urls import path

from .models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock
from . import views

app_name = "netbox_smartlock"

urlpatterns = [
    # --- Access Request ---
    path("access-requests/", views.AccessRequestListView.as_view(), name="accessrequest_list"),
    path("access-requests/add/", views.AccessRequestEditView.as_view(), name="accessrequest_add"),
    path("access-requests/import/", views.AccessRequestImportView.as_view(), name="accessrequest_bulk_import"),
    path("access-requests/import/", views.AccessRequestImportView.as_view(), name="accessrequest_import"),
    path("access-requests/edit/", views.AccessRequestBulkEditView.as_view(), name="accessrequest_bulk_edit"),
    path("access-requests/rename/", views.AccessRequestBulkRenameView.as_view(), name="accessrequest_bulk_rename"),
    path("access-requests/delete/", views.AccessRequestBulkDeleteView.as_view(), name="accessrequest_bulk_delete"),
    path("access-requests/<int:pk>/", views.AccessRequestView.as_view(), name="accessrequest"),
    path("access-requests/<int:pk>/edit/", views.AccessRequestEditView.as_view(), name="accessrequest_edit"),
    path("access-requests/<int:pk>/delete/", views.AccessRequestDeleteView.as_view(), name="accessrequest_delete"),
    path("access-requests/<int:pk>/send/", views.AccessRequestSendView.as_view(), name="accessrequest_send"),
    path("access-requests/<int:pk>/confirm/", views.AccessRequestConfirmView.as_view(), name="accessrequest_confirm"),
    path("access-requests/<int:pk>/accept/", views.AccessRequestAcceptView.as_view(), name="accessrequest_accept"),
    path("access-requests/<int:pk>/reject/", views.AccessRequestRejectView.as_view(), name="accessrequest_reject"),
    path("access-requests/<int:pk>/complete/", views.AccessRequestCompleteView.as_view(), name="accessrequest_complete"),
    path(
        "access-requests/<int:pk>/changelog/",
        views.AccessRequestChangeLogView.as_view(),
        name="accessrequest_changelog",
        kwargs={"model": AccessRequest},
    ),

    # --- Access Request Person ---
    path("access-request-persons/", views.AccessRequestPersonListView.as_view(), name="accessrequestperson_list"),
    path("access-request-persons/add/", views.AccessRequestPersonEditView.as_view(), name="accessrequestperson_add"),
    path("access-request-persons/import/", views.AccessRequestPersonImportView.as_view(), name="accessrequestperson_bulk_import"),
    path("access-request-persons/import/", views.AccessRequestPersonImportView.as_view(), name="accessrequestperson_import"),
    path("access-request-persons/edit/", views.AccessRequestPersonBulkEditView.as_view(), name="accessrequestperson_bulk_edit"),
    path("access-request-persons/delete/", views.AccessRequestPersonBulkDeleteView.as_view(), name="accessrequestperson_bulk_delete"),
    path("access-request-persons/<int:pk>/", views.AccessRequestPersonView.as_view(), name="accessrequestperson"),
    path("access-request-persons/<int:pk>/edit/", views.AccessRequestPersonEditView.as_view(), name="accessrequestperson_edit"),
    path("access-request-persons/<int:pk>/delete/", views.AccessRequestPersonDeleteView.as_view(), name="accessrequestperson_delete"),
    path("access-request-persons/<int:pk>/verify-valid/", views.AccessRequestPersonVerifyValidView.as_view(), name="accessrequestperson_verify_valid"),
    path("access-request-persons/<int:pk>/verify-invalid/", views.AccessRequestPersonVerifyInvalidView.as_view(), name="accessrequestperson_verify_invalid"),
    path("access-request-persons/<int:pk>/in/", views.AccessRequestPersonInView.as_view(), name="accessrequestperson_in"),
    path("access-request-persons/<int:pk>/out/", views.AccessRequestPersonOutView.as_view(), name="accessrequestperson_out"),
    path(
        "access-request-persons/<int:pk>/changelog/",
        views.AccessRequestPersonChangeLogView.as_view(),
        name="accessrequestperson_changelog",
        kwargs={"model": AccessRequestPerson},
    ),

    # --- SmartLock ---
    path("smartlocks/", views.SmartLockListView.as_view(), name="smartlock_list"),
    path("smartlocks/add/", views.SmartLockEditView.as_view(), name="smartlock_add"),
    path("smartlocks/import/", views.SmartLockImportView.as_view(), name="smartlock_bulk_import"),
    path("smartlocks/import/", views.SmartLockImportView.as_view(), name="smartlock_import"),
    path("smartlocks/<int:pk>/", views.SmartLockView.as_view(), name="smartlock"),
    path("smartlocks/<int:pk>/edit/", views.SmartLockEditView.as_view(), name="smartlock_edit"),
    path("smartlocks/<int:pk>/delete/", views.SmartLockDeleteView.as_view(), name="smartlock_delete"),
    path(
        "smartlocks/<int:pk>/changelog/",
        views.SmartLockChangeLogView.as_view(),
        name="smartlock_changelog",
        kwargs={"model": SmartLock},
    ),

    # --- AssetGroup --- (model_name = assetgroup)
    path("asset-groups/", views.AssetGroupListView.as_view(), name="assetgroup_list"),
    path("asset-groups/add/", views.AssetGroupEditView.as_view(), name="assetgroup_add"),
    path("asset-groups/import/", views.AssetGroupImportView.as_view(), name="assetgroup_bulk_import"),
    path("asset-groups/import/", views.AssetGroupImportView.as_view(), name="assetgroup_import"),
    path("asset-groups/<int:pk>/", views.AssetGroupView.as_view(), name="assetgroup"),
    path("asset-groups/<int:pk>/edit/", views.AssetGroupEditView.as_view(), name="assetgroup_edit"),
    path("asset-groups/<int:pk>/delete/", views.AssetGroupDeleteView.as_view(), name="assetgroup_delete"),
    path(
        "asset-groups/<int:pk>/changelog/",
        views.AssetGroupChangeLogView.as_view(),
        name="assetgroup_changelog",
        kwargs={"model": AssetGroup},
    ),

    # --- Asset backed by DCIM Device ---
    path("assets/devices/", views.DeviceAssetListView.as_view(), name="device_asset_list"),
    path("assets/devices/", views.DeviceAssetListView.as_view(), name="asset_list"),
    path("assets/devices/add/", views.DeviceAssetEditView.as_view(), name="device_asset_add"),
    path("assets/devices/add/", views.DeviceAssetEditView.as_view(), name="asset_add"),
    path("assets/devices/<int:pk>/", views.DeviceAssetView.as_view(), name="device_asset"),
    path("assets/devices/<int:pk>/", views.DeviceAssetView.as_view(), name="asset"),
    path("assets/devices/<int:pk>/edit/", views.DeviceAssetEditView.as_view(), name="device_asset_edit"),
    path("assets/devices/<int:pk>/edit/", views.DeviceAssetEditView.as_view(), name="asset_edit"),
    path("assets/devices/<int:pk>/delete/", views.DeviceAssetDeleteView.as_view(), name="device_asset_delete"),
    path("assets/devices/<int:pk>/delete/", views.DeviceAssetDeleteView.as_view(), name="asset_delete"),
    path("assets/devices/<int:pk>/files/", views.DeviceAssetFileView.as_view(), name="device_asset_files"),
    path(
        "assets/devices/<int:pk>/changelog/",
        views.ScopedObjectChangeLogView.as_view(),
        name="asset_changelog",
        kwargs={"model": Asset},
    ),
]
