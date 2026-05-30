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
            "Thiết bị",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:smartlock_list",
                    link_text="Khóa thông minh",
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
        (
            "Danh mục",
            (
                PluginMenuItem(
                    link="plugins:netbox_smartlock:assetgroup_list",
                    link_text="Nhóm tài sản",
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
    ),
    icon_class="mdi mdi-lock-smart",
)
