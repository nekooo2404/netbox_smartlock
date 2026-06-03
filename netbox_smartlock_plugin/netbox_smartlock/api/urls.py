from netbox.api.routers import NetBoxRouter
from . import views

router = NetBoxRouter()
router.register("access-requests", views.AccessRequestViewSet)
router.register("access-request-persons", views.AccessRequestPersonViewSet)
router.register("asset-groups", views.AssetGroupViewSet)
router.register("assets", views.AssetViewSet)
router.register("smartlocks", views.SmartLockViewSet)
urlpatterns = router.urls
