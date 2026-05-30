from netbox.object_actions import (
    AddObject,
    BulkDelete,
    BulkEdit,
    BulkExport,
    BulkImport,
    BulkRename,
    CloneObject,
    DeleteObject,
    EditObject,
)

from .mapping import (
    WARRANTY_STATE_EXPIRED,
    WARRANTY_STATE_EXPIRING,
    WARRANTY_STATE_MISSING,
    WARRANTY_STATE_VALID,
)


ASSET_GROUP_STATUS_LABELS = {
    "active": "Đang hoạt động",
    "inactive": "Không hoạt động",
}

SMARTLOCK_STATUS_LABELS = {
    "active": "Đang hoạt động",
    "backup": "Dự phòng",
    "maintenance": "Bảo trì",
    "broken": "Hỏng",
}

ACCESS_REQUEST_STATUS_LABELS = {
    "draft": "Bản nháp",
    "submitted": "Đã gửi",
    "confirmed": "Đã xác nhận",
    "accepted": "Đã chấp nhận",
    "rejected": "Đã từ chối",
    "completed": "Đã hoàn thành",
}

ACCESS_REQUEST_PERSON_VERIFY_LABELS = {
    "pending": "Chờ xác minh",
    "valid": "Hợp lệ",
    "invalid": "Không hợp lệ",
}

ACCESS_REQUEST_PERSON_ACCESS_LABELS = {
    "out": "Out",
    "in": "In",
}

ACCESS_REQUEST_HISTORY_ACTION_LABELS = {
    "create": "Tạo mới",
    "update": "Cập nhật",
    "submit": "Gửi yêu cầu",
    "confirm": "Xác nhận",
    "accept": "Chấp nhận",
    "reject": "Từ chối",
    "complete": "Hoàn thành",
    "verify_valid": "Xác minh hợp lệ",
    "verify_invalid": "Xác minh không hợp lệ",
    "in": "In",
    "out": "Out",
}

RACK_FACE_LABELS = {
    "front": "Mặt trước",
    "rear": "Mặt sau",
}

WARRANTY_STATE_LABELS = {
    WARRANTY_STATE_VALID: "Còn bảo hành",
    WARRANTY_STATE_EXPIRING: "Sắp hết hạn",
    WARRANTY_STATE_EXPIRED: "Hết hạn",
    WARRANTY_STATE_MISSING: "Chưa thiết lập",
}


def label_for(mapping, value):
    """Trả label tiếng Việt cho giá trị lưu trong DB, fallback an toàn cho dữ liệu lạ."""
    return mapping.get(value, value or "-")


def choices_with_labels(choices, labels):
    """Giữ nguyên value DB/import nhưng thay label hiển thị bằng tiếng Việt."""
    return tuple((value, labels.get(value, label)) for value, label in choices)


class VietnameseAddObject(AddObject):
    label = "Thêm"


class VietnameseBulkImport(BulkImport):
    label = "Import"


class VietnameseBulkEdit(BulkEdit):
    label = "Sửa đã chọn"


class VietnameseBulkRename(BulkRename):
    label = "Đổi tên đã chọn"


class VietnameseBulkExport(BulkExport):
    label = "Xuất"


class VietnameseBulkDelete(BulkDelete):
    label = "Xóa đã chọn"


class VietnameseCloneObject(CloneObject):
    label = "Nhân bản"


class VietnameseEditObject(EditObject):
    label = "Sửa"


class VietnameseDeleteObject(DeleteObject):
    label = "Xóa"


VIETNAMESE_LIST_ACTIONS = (
    VietnameseAddObject,
    VietnameseBulkImport,
    VietnameseBulkExport,
    VietnameseBulkEdit,
    VietnameseBulkRename,
    VietnameseBulkDelete,
)

VIETNAMESE_LIST_ACTIONS_WITHOUT_RENAME = (
    VietnameseAddObject,
    VietnameseBulkImport,
    VietnameseBulkExport,
    VietnameseBulkEdit,
    VietnameseBulkDelete,
)

VIETNAMESE_DETAIL_ACTIONS = (
    VietnameseCloneObject,
    VietnameseEditObject,
    VietnameseDeleteObject,
)
