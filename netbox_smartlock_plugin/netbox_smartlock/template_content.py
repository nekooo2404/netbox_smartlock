from django.core.exceptions import ObjectDoesNotExist
from netbox.plugins import PluginTemplateExtension

from .upload_files import files_for_object


class DeviceAssetContent(PluginTemplateExtension):
    models = ("dcim.device",)

    def get_asset(self):
        try:
            return self.context["object"].smartlock_asset
        except (AttributeError, ObjectDoesNotExist):
            return None

    def buttons(self):
        asset = self.get_asset()
        if asset is None:
            return ""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.has_perm("netbox_smartlock.change_asset", asset):
            return ""
        return self.render(
            "netbox_smartlock/inc/device_asset_file_button.html",
            {"asset": asset},
        )

    def alerts(self):
        asset = self.get_asset()
        if asset is None:
            return ""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not user.has_perm("netbox_smartlock.view_asset", asset):
            return ""
        return self.render(
            "netbox_smartlock/inc/device_asset_file_panel.html",
            {
                "asset": asset,
                "uploaded_files": files_for_object(asset, model_name="asset"),
            },
        )


template_extensions = (DeviceAssetContent,)
