"""Thông điệp nghiệp vụ dùng chung cho SmartLock và phiếu vào ra."""

ACCESS_REQUEST_ADMIN_CRUD_MESSAGE = (
    "Admin phải dùng các hành động workflow thay vì thao tác CRUD phiếu yêu cầu thông thường."
)
ACCESS_REQUEST_PERSON_ADMIN_CRUD_MESSAGE = (
    "Admin phải dùng các hành động workflow thay vì thao tác CRUD đối tượng thông thường."
)
ACCESS_REQUEST_GUEST_EDIT_DENIED_MESSAGE = (
    "Guest không thể sửa phiếu yêu cầu đã chấp nhận hoặc đã hoàn thành."
)
ACCESS_REQUEST_GUEST_DELETE_DENIED_MESSAGE = (
    "Guest không thể xóa phiếu yêu cầu đã chấp nhận hoặc đã hoàn thành."
)
ACCESS_REQUEST_PERSON_EDIT_DENIED_MESSAGE = "Không thể sửa đối tượng này ở trạng thái workflow hiện tại."
ACCESS_REQUEST_PERSON_DELETE_DENIED_MESSAGE = "Không thể xóa đối tượng này ở trạng thái workflow hiện tại."

ACCESS_REQUEST_SEND_PERMISSION_MESSAGE = "Chỉ người tạo phiếu có quyền thay đổi đúng phiếu mới được gửi yêu cầu."
ACCESS_REQUEST_WORKFLOW_PERMISSION_MESSAGE = (
    "Chỉ Admin có quyền thay đổi NetBox mới được thao tác workflow phiếu yêu cầu."
)
ACCESS_REQUEST_OBJECT_WORKFLOW_PERMISSION_MESSAGE = (
    "Chỉ Admin có quyền thay đổi đúng phiếu này mới được thao tác workflow."
)
ACCESS_REQUEST_PERSON_WORKFLOW_PERMISSION_MESSAGE = (
    "Chỉ Admin có quyền thay đổi NetBox mới được thao tác workflow đối tượng."
)
ACCESS_REQUEST_PERSON_OBJECT_WORKFLOW_PERMISSION_MESSAGE = (
    "Chỉ Admin có quyền thay đổi đúng đối tượng này mới được thao tác workflow."
)

ACCESS_REQUEST_EDIT_LOCKED_MESSAGE = "Không thể sửa phiếu yêu cầu đã chấp nhận hoặc đã hoàn thành."
ACCESS_REQUEST_PERSON_FILE_REQUIRED_MESSAGE = "Bắt buộc có ít nhất một file đính kèm."
ACCESS_REQUEST_PERSON_SCOPE_DENIED_MESSAGE = "Bạn không có quyền thêm đối tượng vào phiếu yêu cầu này."
ACCESS_REQUEST_PERSON_IMPORT_SCOPE_DENIED_MESSAGE = "Bạn không có quyền import đối tượng vào phiếu yêu cầu này."
ACCESS_REQUEST_PERSON_EDIT_LOCKED_MESSAGE = (
    "Không thể thêm hoặc sửa đối tượng sau khi phiếu yêu cầu đã chấp nhận hoặc hoàn thành."
)
ACCESS_REQUEST_PERSON_IMPORT_LOCKED_MESSAGE = (
    "Không thể import đối tượng sau khi phiếu yêu cầu đã chấp nhận hoặc hoàn thành."
)
ACCESS_REQUEST_PERSON_SCOPED_REQUEST_UNAVAILABLE_MESSAGE = "Phiếu yêu cầu theo phạm vi hiện không khả dụng."
ACCESS_REQUEST_REQUIRED_MESSAGE = "Bắt buộc chọn phiếu yêu cầu."
ACCESS_REQUEST_PERSON_VERIFY_REQUIRES_CONFIRMED_MESSAGE = (
    "Chỉ được xác minh đối tượng sau khi Admin xác nhận phiếu yêu cầu."
)
