# 📘 README - upload_file_plugin

## 1. Giới thiệu
`upload_file_plugin` là một **plugin mở rộng cho NetBox**, được phát triển nhằm **hỗ trợ upload nhiều ảnh cùng lúc cho các đối tượng trong hệ thống DCIM**.
Plugin này hoạt động như một trường thông tin trong form nhập liệu, cho phép người dùng chọn và upload nhiều ảnh trực tiếp khi tạo hoặc chỉnh sửa đối tượng.

Các tính năng nổi bật:
- Upload nhiều ảnh cùng lúc (hỗ trợ các định dạng phổ biến: jpg, jpeg, png, gif, webp, bmp).
- Giao diện kéo thả hoặc chọn file đơn giản, trực quan ngay trong form nhập liệu.
- Hiển thị danh sách ảnh vừa upload trong form.
- Không hỗ trợ quản lý, xóa, tải về hoặc chỉnh sửa file sau khi lưu.

## 2. Chức năng chính
- Thêm trường upload ảnh vào form nhập/chỉnh sửa đối tượng trên NetBox.
- Hỗ trợ upload nhiều ảnh cùng lúc.
- Hiển thị danh sách ảnh vừa upload trong form nhập liệu.
- File đã lưu chỉ hiển thị tên file; không cung cấp link tải, nút xóa hoặc chỉnh sửa file sau khi lưu.
- Tương thích với NetBox 3.6+ và Python 3.9+.
- Dễ dàng tích hợp với các plugin quản lý tài sản khác.

## 3. Cài đặt

### 3.1. Cài đặt Online (khuyến nghị)
Di chuyển vào server NetBox và kích hoạt virtualenv
```bash
source /opt/netbox/venv/bin/activate
```
Cài trực tiếp từ GitLab (branch production)
```bash
pip install git+https://gitlab.gtsc.vn/gtsc-dev/upload_file_plugin.git@production
```
Sau khi cài đặt, plugin cần được kích hoạt trong `configuration.py`:
```no-highlight
vi /opt/netbox/netbox/netbox/configuration.py
```
```python
PLUGINS = ["upload_file_plugin"]
```

Khởi động lại NetBox:
```bash
sudo systemctl restart netbox netbox-worker
```

### 3.2. Cài đặt Offline
Trên máy có Internet:
```bash
git clone -b production https://gitlab.gtsc.vn/gtsc-dev/upload_file_plugin.git
cd upload_file_plugin
python3 -m pip wheel . -w dist
```
Copy file .whl trong thư mục dist/ sang server NetBox.
Trên server NetBox:
```bash
source /opt/netbox/venv/bin/activate
pip install /opt/netbox/netbox/plugins/upload_file_plugin-*.whl
```

Cấu hình `configuration.py` và restart NetBox như phần Online.

## 4. Tích hợp vào form plugin khác

Plugin cung cấp `UploadFileFormMixin` để gắn trường upload ảnh vào `NetBoxModelForm`.

```python
from netbox.forms import NetBoxModelForm
from upload_file_plugin.integration import UploadFileFormMixin


class AssetForm(UploadFileFormMixin, NetBoxModelForm):
    upload_file_model_name = "asset"

    fieldsets = (
        # thêm "upload_files" vào FieldSet mong muốn
    )

    class Meta:
        model = Asset
        fields = (
            # các field của object
        )
```

Trong detail view, dùng `get_uploaded_files()` nếu cần hiển thị tên ảnh đã lưu:

```python
from upload_file_plugin.integration import get_uploaded_files


uploaded_files = get_uploaded_files(instance, model_name="asset")
```
