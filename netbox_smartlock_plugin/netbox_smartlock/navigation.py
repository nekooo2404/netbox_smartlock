from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem

_BTN_GREEN = "green"

menu = PluginMenu(
    label="SmartLock",
    groups=(
        (
            "Security Control",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:accessrequest_list",
                    link_text="Access Requests",
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_smartlock:accessrequest_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            color=_BTN_GREEN,
                        ),
                    ),
                ),
            ),
        ),
        (
            "Devices",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:smartlock_list",
                    link_text="Smart Locks",
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_smartlock:smartlock_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            color=_BTN_GREEN,
                        ),
                    ),
                ),
            ),
        ),
        (
            "Catalog",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:assetgroup_list",
                    link_text="Asset Groups",
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_smartlock:assetgroup_add",
                            title="Add",
                            icon_class="mdi mdi-plus-thick",
                            color=_BTN_GREEN,
                        ),
                    ),
                ),
            ),
        ),
    ),
    icon_class="mdi mdi-lock-smart",
)
