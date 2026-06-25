from netbox.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem

_BTN_GREEN = "green"

menu = PluginMenu(
    label="SmartLock",
    groups=(
        (
            "Kiểm soát an ninh",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:accessrequest_list",
                    link_text="Phiếu yêu cầu vào ra",
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_smartlock:accessrequest_add",
                            title="Thêm",
                            icon_class="mdi mdi-plus-thick",
                            color=_BTN_GREEN,
                        ),
                    ),
                ),
            ),
        ),
        (
            "Tài sản",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:asset_list",
                    link_text="Quản lý tài sản",
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_smartlock:asset_add",
                            title="Thêm",
                            icon_class="mdi mdi-plus-thick",
                            color=_BTN_GREEN,
                        ),
                    ),
                ),
                PluginMenuItem(
                    link="plugins:netbox_smartlock:assetgroup_list",
                    link_text="Quản lý nhóm tài sản",
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_smartlock:assetgroup_add",
                            title="Thêm",
                            icon_class="mdi mdi-plus-thick",
                            color=_BTN_GREEN,
                        ),
                    ),
                ),
            ),
        ),
        (
            "Thiết bị an ninh vật lý",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:smartlock_list",
                    link_text="Quản lý smart lock",
                    buttons=(
                        PluginMenuButton(
                            link="plugins:netbox_smartlock:smartlock_add",
                            title="Thêm",
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
