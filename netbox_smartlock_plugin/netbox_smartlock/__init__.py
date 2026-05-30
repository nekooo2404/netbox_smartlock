from netbox.plugins import PluginConfig


class SmartLockConfig(PluginConfig):
    name = "netbox_smartlock"
    verbose_name = "NetBox SmartLock"
    description = "Quản lý khóa thông minh trong NetBox"
    version = "0.1.0"
    base_url = "smartlock"
    min_version = "4.6.0"
    max_version = "4.6.99"
    default_settings = {}


config = SmartLockConfig
