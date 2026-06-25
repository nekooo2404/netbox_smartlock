**_Tài liệu đặc tả yêu cầu phần mềm_**

| **Mã dự án** |     |
| --- | --- |
| **Mã tài liệu** |     |
| --- | --- |
| **Ngày** | **2026** |
| --- | --- |

**TRANG KÝ**

**NGƯỜI LẬP:** ………………… &lt;Ngày&gt;

BA

**NGƯỜI KIỂM TRA:** &lt;Ngày&gt;

PM

**NGƯỜI PHÊ DUYỆT:** &lt;Tên&gt; &lt;Ngày&gt;

&lt;Vị trí&gt;

**MỤC LỤC**

# **_GIỚI THIỆU_**

## **_Mục đích tài liệu_**

## **_Phạm vi hệ thống_**

## **_Định nghĩa thuật ngữ viết tắt_**

| **STT** | **Nội dung** | **Ý nghĩa** |
| --- | --- | --- |
| 1   |     |     |
| --- | --- | --- |
| 2   |     |     |
| --- | --- | --- |
|     |     |     |
| --- | --- | --- |
|     |     |     |
| --- | --- | --- |

## **_Tài liệu tham khảo_**

| **STT** | **Tên tài liệu** |
| --- | --- |
| 1   |     |
| --- | --- |
| 2   |     |
| --- | --- |
| 3   |     |
| --- | --- |
| 4   |     |
| --- | --- |

## Mô tả tài liệu

Nội dung tài liệu này bao gồm các phần:

1.  Giới thiệu
2.  Tổng quan hệ thống
3.  Yêu cầu chức năng người sử dụng
4.  Các yêu cầu khác
5.  Tiêu chuẩn nghiệm thu hệ thống

## Lịch sử thay đổi

| **STT** | **Phiên bản** | **Màu sắc** |
| --- | --- | --- |
| 1   | V1  | 03/03/26 |
| --- | --- | --- |
| 2   |     |     |
| --- | --- | --- |
| 3   |     |     |
| --- | --- | --- |
| 4   |     |     |
| --- | --- | --- |

# 2.TỔNG QUAN HỆ THỐNG

## Phát biểu bài toán Mục tiêu hệ thốngNgười sử dụng hệ thống

| **Người sử dụng** | **Mô tả** |
| --- | --- |
| Admin | Là người vận hành toàn bộ hệ thống. Có quyền cấu hình, phân quyền người dùng, tạo/sửa/xóa tài khoản, thiết lập tham số hệ thống, và giám sát hoạt động của các đơn vị. |
| --- | --- |
| Guest User | Là khách hàng/đối tác có hợp đồng thuê chỗ đặt thiết bị, rack hoặc dịch vụ tại Data Center và có nhu cầu vào/ra để thực hiện công việc liên quan. |
| --- | --- |
|     |     |
| --- | --- |
|     |     |
| --- | --- |
|     |     |
| --- | --- |
|     |     |
| --- | --- |
|     |     |
| --- | --- |

## Mô tả quy trình xử lý nghiệp vụ

# 3.ĐẶC TẢ YÊU CẦU CHỨC NĂNG WEB

### Quản lý phiếu yêu cầu vào ra - Guest User

1.  Mô tả nghiệp vụ

- \- Chức năng cho phép người dùng có vai trò khách hàng/ đối tượng quản lý danh sách phiếu yêu cầu ra vào trung tâm dữ liệu
- \- Người dùng có thể thêm mới, chỉnh sửa, xoá thông tin phiếu yêu cầu, xem danh sách hoặc xem chi tiết thông tin phiếu.

1.  Dòng sự kiện chính

- Người sử dụng chọn chức năng Kiểm soát an ninh -> Quản lý phiếu yêu cầu ra vào Hệ thống hiển thị danh sách phiếu yêu cầu ra vào Trung tâm dữ liệu. Thông tin hiển thị tại danh sách phiếu yêu cầu bao gồm:
    - Tên phiếu (Click ra màn hình xem chi tiết)
    - Trạng thái phiếu
    - Lý do
    - Ngày dự kiến
    - Region
    - Site
    - Người tạo
    - Thời gian tạo
    - Thời gian cập nhật
    - Thao tác: Xoá/ Sửa
- Màn hình danh sách phiếu yêu cầu
- Tại danh sách phiếu yêu cầu , sắp xếp theo thứ tự thời gian cập nhật mới nhất lên đầu tiên.
- Chức năng “Tìm kiếm”, nhập giá trị để tìm kiếm phiếu yêu cầu theo các tiêu chí:Tên phiếu, trạng thái
- Chức năng “Configure Table”: cho phép người dùng lựa chọn các trường thông tin hiển thị ngoài màn hình danh sách
- Chức năng “Export excel”: cho phép người dùng export danh sách phiếu yêu cầu ra file excel
- Thêm mới phiếu yêu cầu

Chức năng “Thêm mới”: cho phép người dùng thực hiện thêm mới phiếu yêu cầu

<div class="joplin-table-wrapper"><table><thead><tr><th><p><strong>Thông tin</strong></p></th><th><p><strong>Kiểu</strong></p></th><th><p><strong>Bắt buộc</strong></p></th><th><p><strong>Mô tả</strong></p></th></tr><tr><th><p>Tên phiếu</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Là tên của phiếu yêu cầu</p><p>- Cho phép nhập tối đa 100 ký tự</p><p>- Tên phiếu là duy nhất</p></th></tr><tr><th><p>Ngày dự kiến</p></th><th><p>Datepicker</p></th><th><p>x</p></th><th><p>- Chọn ngày dự kiến vào</p><p>- Cho phép nhập/ chọn thông tin ngày</p><p>- Placeholder: dd/mm/yyyy</p></th></tr><tr><th><p>Lý do</p></th><th><p>Textarea</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 500 ký tự</p></th></tr><tr><th><p>Region</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách Region theo phân quyền của người tạo phiếu. Không cho phép chọn ngoài phạm vi được cấp quyền.</p></th></tr><tr><th><p>Site</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách Site theo giá trị Region được chọn ở trên</p></th></tr><tr><th><p>Lưu</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình chi tiết phiếu yêu cầu</li></ol></th></tr><tr><th><p>Huỷ</p></th><th><p>Button</p></th><th><p></p></th><th><p>- Hiển thị popup xác nhận Hủy lưu thông tin<br>+ Bấm Có: Đóng popup xác nhận và popup thêm mới, quay lại màn hình danh sách, không cập nhật CSDL, điều hướng người dùng về màn hình danh sách Phiếu yêu cầu<br>+ Bấm Không: Đóng popup xác nhận, giữ nguyên popup Thêm mới/ chỉnh sửa với các thông tin dữ liệu người dùng đang nhập</p></th></tr></thead></table></div>

- Chỉnh sửa phiếu yêu cầu
- Button Chỉnh sửa chỉ hiển thị khi chưa được Admin Chấp nhận
- Chọn chức năng “Chỉnh sửa”, hệ thống hiển thị các thông tin đã được cập nhật trước đó, cho phép người dùng chỉnh sửa các thông tin:

| **Thông tin** | **Kiểu** | **Bắt buộc** | **Mô tả** |
| --- | --- | --- | --- |
| Tên phiếu | Textbox | x   | \- Là tên của phiếu yêu cầu<br><br>\- Cho phép nhập tối đa 100 ký tự<br><br>\- Tên phiếu là duy nhất |
| --- | --- | --- | --- |
| Ngày dự kiến | Datepicker | x   | \- Chọn ngày dự kiến vào<br><br>\- Cho phép nhập/ chọn thông tin ngày<br><br>\- Placeholder: dd/mm/yyyy |
| --- | --- | --- | --- |
| Lý do | Textarea | x   | \- Cho phép nhập tối đa 500 ký tự |
| --- | --- | --- | --- |
| Region | Selectbox |     | \- Hiển thị danh sách Region theo phân quyền của người tạo phiếu. Không cho phép chọn ngoài phạm vi được cấp quyền. |
| --- | --- | --- | --- |
| Site | Selectbox |     | \- Hiển thị danh sách Site theo giá trị Region được chọn ở trên |
| --- | --- | --- | --- |
| Huỷ | Button |     | Hiển thị popup xác nhận Hủy lưu thông tin  <br>\- Hủy: Đóng popup xác nhận và popup chỉnh sửa, quay lại màn hình danh sách, không cập nhật CSDL  <br>\- Không hủy: Đóng popup xác nhận, giữ nguyên popup thêm mới với các thông tin dữ liệu người dùng đang nhập |
| --- | --- | --- | --- |
| Cập nhật | Button |     | Kiểm tra điều kiện:<br><br>\- Thỏa mãn: Đóng popup chỉnh sửa, cập nhật thông tin trong CSDL, hiển thị thông báo thành công cho người dùng<br><br>\- Không thỏa mãn: Thông báo lỗi người dùng |
| --- | --- | --- | --- |

- Xoá phiếu yêu cầu
- Chức năng xoá chỉ hiển thị khi phiếu yêu cầu chưa được Hoàn thành
- Chọn chức năng “Xoá”, hệ thống hiển thị popup xác nhận Xoá phiếu. Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác. Trường hợp người dùng Xác nhận, hệ thống xoá phiếu khỏi CSDL.
- Chi tiết phiếu yêu cầu
- Người dùng click vào tên phiếu để xem chi tiết phiếu yêu cầu
- Chọn chức năng “Xem chi tiết”, hệ thống hiển thị cửa sổ thông tin chi tiết phiếu yêu bao gồm:

\+ Button: Gửi/ Sửa/ Xoá

- - - - - Gửi:

Button này chỉ hiển thị khi đã tồn tại ít nhất một đối tượng

Gửi phiếu đến cán bộ thuộc nhóm Admin và gửi email thông báo đến cán bộ thuộc nhóm Admin

- - - - - Sửa: Hiển thị màn hình chỉnh sửa phiếu yêu cầu
                - Xoá: Hiển thị màn hình xác nhận xoá

\+ Các tab

\- Phiếu yêu cầu ra vào: Hiển thị các trường thông tin phiếu yêu cầu đã tạo bao gồm các trường thông tin:

- - - - - Tên
                - Ngày dự kiến
                - Mô tả
                - Trạng thái
                - Region
                - Site

\- Lịch sử yêu cầu: Hiển thị danh sách thao tác của người dùng:

- - - - - Người thực hiện
                - Hoạt động
                - Trạng thái
                - Thời gian
                - Mô tả

\- Nhật ký thay đổi: hiển thị danh sách lịch sử thay đổi trên phiếu yêu cầu bao gồm các trường thông tin:

- - - - - Thời gian
                - Tên người dùng
                - Họ và tên đầy đủ
                - Hoạt động
                - Type
                - Đối tượng
                - Request ID

\- Đối tượng: Hiển thị danh sách đối tượng đăng ký ra vào trung tâm dữ liệu:

- - - - - Tại danh sách đối tương trong phiếu yêu cầu , sắp xếp theo thứ tự thời gian cập nhật mới nhất lên đầu tiên.
        - Mã định danh
        - Họ tên (Click ra màn hình xem chi tiết)
        - Đơn vị
        - Chức vụ
        - Trạng thái
        - Ngày tạo
        - Thời gian cập nhật
        - Tệp đính kèm
        - Xác nhận
        - Action: Sửa/ xoá
            - - Chức năng “Nhập dữ liệu”: cho phép người dùng thực hiện thêm mới đối tượng bằng cách import bằng file
- Thêm mới đối tượng

Chức năng “Thêm mới đối tượng”: cho phép người dùng thực hiện thêm mới đối tượng trong phiếu yêu cầu. Khi click vào hiển thị màn hình thêm mới đối tượng

<div class="joplin-table-wrapper"><table><thead><tr><th><p><strong>Thông tin</strong></p></th><th><p><strong>Kiểu</strong></p></th><th><p><strong>Bắt buộc</strong></p></th><th><p><strong>Mô tả</strong></p></th></tr><tr><th><p></p></th><th><p></p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Mã định danh</p></th><th><p>textbox</p></th><th><p>x</p></th><th><p>- Nhập đủ 12 ký tự</p><p>- Là số duy nhất trong 1 phiếu</p></th></tr><tr><th><p>Họ và tên</p></th><th><p>textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 50 ký tự</p></th></tr><tr><th><p>Đơn vị</p></th><th><p>textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Chức danh</p></th><th><p>textbox</p></th><th><p></p></th><th><p>- Cho phép nhập tối đa 50 ký tự</p></th></tr><tr><th><p>Số điện thoại</p></th><th><p>textbox</p></th><th><p></p></th><th><p>- Chỉ cho phép nhập ký tự số (0-9)</p><p>- Độ dài: 10</p><p>- Đúng định dạng số điện thoại Việt Nam</p></th></tr><tr><th><p>Location</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách Location theo giá trị Site được chọn ở phiếu yêu cầu</p></th></tr><tr><th><p>Mô tả</p></th><th><p>Textarea</p></th><th><p></p></th><th><p>- Cho phép nhập tối đa 500 ký tự</p></th></tr><tr><th><p>File đính kèm</p></th><th><p>Upload file</p></th><th><p>x</p></th><th><p>- Cho phép uploadd nhiều file</p><p>- Định dạng: jpg, jpeg, png,..</p><p>- Dung lượng &lt;=25MB</p></th></tr><tr><th><p>Lưu</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình danh sách đối tượng</li></ol></th></tr><tr><th><p>Huỷ</p></th><th><p>Button</p></th><th><p></p></th><th><p>- Hiển thị popup xác nhận Hủy lưu thông tin<br>+ Bấm Có: Đóng popup xác nhận và popup thêm mới, quay lại màn hình danh sách, không cập nhật CSDL, điều hướng người dùng về màn hình danh danh sách đói tượng<br>+ Bấm Không: Đóng popup xác nhận, giữ nguyên popup Thêm mới/ chỉnh sửa với các thông tin dữ liệu người dùng đang nhập</p></th></tr><tr><th><p>Tạo và thêm cái khác</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình thêm mới đối tượng</li></ol></th></tr></thead></table></div>

- Chỉnh sửa đối tượng
- Button Chỉnh sửa chỉ hiển thị khi chưa được admin verify hoặc verify là không hợp lệ
- Chọn chức năng “Chỉnh sửa”, hệ thống hiển thị các thông tin đã được cập nhật trước đó, cho phép người dùng chỉnh sửa các thông tin:

| **Thông tin** | **Kiểu** | **Bắt buộc** | **Mô tả** |
| --- | --- | --- | --- |
| Mã định danh | textbox | x   | \- Nhập đủ 12 ký tự<br><br>\- Là số duy nhất trong 1 phiếu |
| --- | --- | --- | --- |
| Họ và tên | textbox | x   | \- Cho phép nhập tối đa 50 ký tự |
| --- | --- | --- | --- |
| Đơn vị | textbox | x   | \- Cho phép nhập tối đa 100 ký tự |
| --- | --- | --- | --- |
| Chức danh | textbox |     | \- Cho phép nhập tối đa 50 ký tự |
| --- | --- | --- | --- |
| Số điện thoại | textbox |     | \- Chỉ cho phép nhập ký tự số (0-9)<br><br>\- Độ dài: 10<br><br>\- Đúng định dạng số điện thoại Việt Nam |
| --- | --- | --- | --- |
| Location | Selectbox |     | \- Hiển thị danh sách Location theo giá trị Site được chọn ở phiếu yêu cầu |
| --- | --- | --- | --- |
| Mô tả | Textarea |     | \- Cho phép nhập tối đa 500 ký tự |
| --- | --- | --- | --- |
| File đính kèm | Upload file | x   | \- Cho phép upload nhiều file<br><br>\- Định dạng: jpg, jpeg, png,..<br><br>\- Dung lượng: tối đa 25MB |
| --- | --- | --- | --- |
| Cập nhật | Button |     | Kiểm tra điều kiện:<br><br>\- Thỏa mãn: Đóng popup chỉnh sửa, cập nhật thông tin trong CSDL, hiển thị thông báo thành công cho người dùng<br><br>\- Không thỏa mãn: Thông báo lỗi người dùng |
| --- | --- | --- | --- |

- Xoá đối tượng
- Chức năng xoá chỉ hiển thị khi đối tượng chưa được verify hoặc verify là không hợp lệ
- Chọn chức năng “Xoá”, hệ thống hiển thị popup xác nhận Xoá đối tượng. Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác. Trường hợp người dùng Xác nhận, hệ thống xoá đối tượng khỏi CSDL.
- Xem chi tiết đối tượng
- Người dùng click vào tên đối tượng để xem thông tin chi tiết
- Chọn chức năng “Xem chi tiết”, hệ thống hiển thị màn hình thông tin chi tiết bao gồm:
    - - Họ và tên
        - Mã định danh
        - Đơn vị
        - Chức danh
        - Số điện thoại
        - Mô tả
        - File đính kèm
        - Trạng thái
        - Xác nhân

1.  Tiền điều kiện

- Người dùng login hệ thống dưới quyền quản trị hệ thống.

1.  Điều kiện rẽ nhánh

- Khi người dùng không nhập đầy đủ các thông tin bắt buộc, hệ thống hiển thị cảnh báo.

1.  Hậu điều kiện

- Xem danh sách, chỉnh sửa , xoá thông tin phiếu yêu cầu, gửi thông tin phiếu yêu cầu

### Quản lý phiếu yêu cầu vào ra - Admin

1.  Mô tả nghiệp vụ

\- Chức năng cho phép người dùng có vai trò quản trị hệ thống quản lý danh sách phiếu yêu cầu ra vào trung tâm dữ liệu

\- Người dùng có thể phê duyệt phiếu, xem danh sách hoặc xem chi tiết thông tin phiếu.

1.  Mô tả nghiệp vụ

\- Người sử dụng chọn chức năng Kiểm soát an ninh -> Quản lý phiếu yêu cầu ra vào Hệ thống hiển thị danh sách phiếu yêu cầu ra vào Trung tâm dữ liệu. Thông tin hiển thị tại danh sách phiếu yêu cầu bao gồm:

- - Tên phiếu (Click ra màn hình xem chi tiết)
    - Trạng thái phiếu
    - Lý do
    - Ngày dự kiến
    - Region
    - Site
    - Người tạo
    - Thời gian tạo
    - Thời gian cập nhật
- Màn hình danh sách phiếu yêu cầu
- Tại danh sách phiếu yêu cầu , sắp xếp theo thứ tự thời gian cập nhật mới nhất lên đầu tiên.
- Chức năng “Tìm kiếm”, nhập giá trị để tìm kiếm phiếu yêu cầu theo các tiêu chí:Tên phiếu, trạng thái
- Chức năng “Configure Table”: cho phép người dùng lựa chọn các trường thông tin hiển thị ngoài màn hình danh sách
- Chức năng “Export excel”: cho phép người dùng export danh sách phiếu yêu cầu ra file excel
- Chi tiết phiếu yêu cầu
- Người dùng click vào tên phiếu để xem chi tiết phiếu yêu cầu
- Chọn chức năng “Xem chi tiết”, hệ thống hiển thị màn hình thông tin chi tiết phiếu yêu bao gồm:

\+ Button: Xác nhận

- - - - - Tiếp nhận phiếu yêu cầu và có thể verify thông tin đối tượng trong phiếu yêu cầu
                - Khi click vào button Xác nhận -> Button Xác nhận ẩn đi và được thay thế bằng button (Chấp nhận/ Từ chối)

\+ Các tab

\- Phiếu yêu cầu ra vào: Hiển thị các trường thông tin phiếu yêu cầu đã tạo bao gồm các trường thông tin:

- - - - - Tên
                - Ngày dự kiến
                - Mô tả
                - Trạng thái
                - Region
                - Site

\- Lịch sử yêu cầu: Hiển thị danh sách thao tác của người dùng:

- - - - - Người thực hiện
                - Hoạt động
                - Trạng thái
                - Thời gian
                - Mô tả

\- Nhật ký thay đổi: hiển thị danh sách lịch sử thay đổi trên phiếu yêu cầu bao gồm các trường thông tin:

- - - - - Thời gian
                - Tên người dùng
                - Họ và tên đầy đủ
                - Hoạt động
                - Type
                - Đối tượng
                - Request ID

\- Đối tượng: Hiển thị danh sách đối tượng đăng ký ra vào trung tâm dữ liệu:

- - - - - Tại danh sách đối tương trong phiếu yêu cầu , sắp xếp theo thứ tự thời gian cập nhật mới nhất lên đầu tiên.
        - Mã định danh
        - Họ tên (Click ra màn hình xem chi tiết)
        - Đơn vị
        - Chức vụ
        - Trạng thái
        - Ngày tạo
        - Thời gian cập nhật
        - Tệp đính kèm
        - Xác nhận
        - Action: Hợp lệ/ Không hợp lệ (chỉ hiển thị khi admin xác nhận phiếu)
            - Khi click vào hợp lệ -> chuyển trạng thái xác nhận “Hợp lệ”
            - Khi click vào “Không hợp lệ” -> chuyển trạng thái xác nhận thành không hợp lệ
- Xem chi tiết đối tượng
- Người dùng click vào tên đối tượng để xem thông tin chi tiết
- Chọn chức năng “Xem chi tiết”, hệ thống hiển thị màn hình thông tin chi tiết bao gồm:
    - - Họ và tên
        - Mã định danh
        - Đơn vị
        - Chức danh
        - Số điện thoại
        - Mô tả
        - File đính kèm
        - Trạng thái
        - Xác nhận
- Chấp nhận/ Từ chối phiếu yêu cầu
    - Chọn chức năng “Từ chối”
        - Hệ thống hiển thị popup nhập lý do từ chối phiếu yêu cầu.
            - Lý do: textarea
            - Button Huỷ/ Xác nhận
                - Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác.
                - Trường hợp người dùng Xác nhận, hệ thống trả lại phiếu yêu cầu cho người yêu cầu
        - Sau khi trả lại
            - Hệ thống gửi email thông báo đến người tạo phiếu
            - Admin:Chỉ được phép thông tin chi tiết của phiếu yêu cầu và thông tin đối tượng
            - Người tạo phiếu yêu cầu: có quyền chỉnh sửa, xoá thông tin phiếu yêu cầu, thông tin đối tượng và có thể gửi lại phiếu yêu cầu đến admin
    - Chọn chức năng “Chấp nhận”
        - Khi tồn tại một đối tượng có trạng thái xác nhận “không hợp lệ”, admin chọn “Chấp nhận”, hệ thống hiển thị popup cảnh báo và không thể chấp nhận phiếu yêu cầu
        - Hệ thống hiển thị popup xác nhận chấp nhận phiếu yêu cầu.
            - Lý do: textarea
            - Button Huỷ/ Xác nhận
                - Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác.
                - Trường hợp người dùng Xác nhận, hệ thống chấp nhận phiếu yêu cầu cho người yêu cầu
        - Sau khi chấp nhận phiếu yêu cầu
            - Hệ thống gửi email thông báo đến người tạo phiếu
            - Người tạo phiếu yêu cầu: chỉ có quyền xem thông tin chi tiết phiếu, chi tiết đối tượng, xoá thông tin đối tượng có trong phiếu
            - Admin:
                - Được phép thông tin chi tiết của phiếu yêu cầu, thông tin chi tiết đối tượng
                - Được phép xác nhận thời gian ra vào của đối tượng
- Xác nhận thời gian ra vào của đối tượng

Sau khi phiếu đã được chấp nhận, click vào tab “Danh sách đối tượng” màn hình hiển thị:

- Mã định danh
- Họ tên (Click ra màn hình xem chi tiết)
- Đơn vị
- Chức vụ
- Trạng thái
- Ngày tạo
- Thời gian cập nhật
- Tệp đính kèm
- Xác nhận
- Action:
    - In
        - Hiển thị khi trạng thái của đối tượng “Out”
        - Khi click vào In, trạng thái chuyển thành “Out”
    - Out
        - Hiển thị khi trạng thái đối tượng “In”
        - Khi click vào Out, trạng thái chuyển thành “In”
- Hoàn thành phiếu yêu cầu
- Button “Hoàn thành” hiển thị khi admin đã chấp nhận phiếu yêu cầu.
- Click vào button “Hoàn thành” hệ thống hiển thị popup xác nhận hoàn thành phiếu yêu cầu:
    - - Text: Bạn có muốn hoàn thành phiếu {tên phiếu}?
        - Button Huỷ/ Hoàn thành
            - - Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác.
                - Trường hợp người dùng Hoàn thành, trạng thái phiếu chuyển “Hoàn thành”
        - Sau khi chấp nhận phiếu yêu cầu
            - Hệ thống gửi thông báo đến người tạo phiếu
            - Admin:Chỉ được phép thông tin chi tiết của phiếu yêu cầu và thông tin đối tượng
            - Người tạo phiếu yêu cầu: Chỉ được phép thông tin chi tiết của phiếu yêu cầu và thông tin đối tượng

1.  Tiền điều kiện

- Người dùng login hệ thống dưới quyền quản trị hệ thống.

1.  Điều kiện rẽ nhánh

- Khi người dùng không nhập đầy đủ các thông tin bắt buộc, hệ thống hiển thị cảnh báo.

1.  Hậu điều kiện

- Xem danh sách, chỉnh sửa , phê duyệt phiếu yêu cầu,…

### Quản lý tài sản

### Quản lý nhóm tài sản

1.  Mô tả nghiệp vụ

- Chức năng cho phép người dùng có vai trò quản lý danh sách nhóm tài sản có trong hệ thống
- Người dùng có thể thêm mới, chỉnh sửa, xoá thông tin tài sản, xem danh sách hoặc xem chi tiết nhóm tài sản

1.  Dòng sự kiện chính

- Người sử dụng chọn chức năng Tài sản -> Quản lý nhóm tài sản. Thông tin hiển thị tại danh sách nhóm tài sản bao gồm:
    - Tên (Click ra màn hình xem chi tiết)
    - Mã
    - Trạng thái
    - Mô tả
    - Người tạo
    - Thời gian tạo
    - Thời gian cập nhật
    - Thao tác: Xoá/ Sửa
- Màn hình danh sách tài sản
- Tại danh sách tài sản , sắp xếp theo thứ tự thời gian cập nhật mới nhất lên đầu tiên.
- Chức năng “Tìm kiếm”, nhập giá trị để tìm kiếm nhóm tài sản theo các tiêu chí:Tên, trạng thái
- Chức năng “Configure Table”: cho phép người dùng lựa chọn các trường thông tin hiển thị ngoài màn hình danh sách
- Chức năng “Export excel”: cho phép người dùng export danh sách tài sản ra file excel
- Thêm mới tài sản

Chức năng “Thêm mới”: cho phép người dùng thực hiện thêm mới tài sản

<div class="joplin-table-wrapper"><table><thead><tr><th><p><strong>Thông tin</strong></p></th><th><p><strong>Kiểu</strong></p></th><th><p><strong>Bắt buộc</strong></p></th><th><p><strong>Mô tả</strong></p></th></tr><tr><th><p>Tên</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Mã</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhâp tối đa 50 ký tự</p><p>- Mã là giá trị duy nhất</p></th></tr><tr><th><p>Trạng thái</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Có 2 trạng thái:</p><p>+ Hoạt động</p><p>+ Không hoạt động</p><p>- Mặc định: Hoạt động</p></th></tr><tr><th><p>Mô tả</p></th><th><p>Textarea</p></th><th><p></p></th><th><p>- Cho phép nhập tối đa 500 ký tự</p></th></tr><tr><th><p>File đính kèm</p></th><th><p>File upload</p></th><th><p></p></th><th><p>- Cho phép upload file ảnh: png, jpeg, png</p><p>- Dung lượng tối đa: 25MB</p></th></tr><tr><th><p>Exclude from Visualization:</p></th><th><p>Checbox</p></th><th><p></p></th><th><p>- Khi checked: tất cả tài sản thuộc nhóm tài sản này sẽ được thêm vào visualization</p><p>- Unchecked: các tài sản thuộc nhóm tài sản này sẽ không được thêm vào visualization</p></th></tr><tr><th><p>Tạo mới</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình danh sách</li></ol></th></tr><tr><th><p>Huỷ</p></th><th><p>Button</p></th><th><p></p></th><th><p>- Hiển thị popup xác nhận Hủy lưu thông tin<br>+ Bấm Có: Đóng popup xác nhận và popup thêm mới, quay lại màn hình danh sách, không cập nhật CSDL, điều hướng người dùng về màn hình danh sách nhóm tài sản<br>+ Bấm Không: Đóng popup xác nhận, giữ nguyên popup Thêm mới/ chỉnh sửa với các thông tin dữ liệu người dùng đang nhập</p></th></tr><tr><th><p>Tạo và thêm tiếp</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình thêm mới nhóm tài sản</li></ol></th></tr></thead></table></div>

- Chỉnh sửa nhóm tài sản
- Chọn chức năng “Chỉnh sửa”, hệ thống hiển thị các thông tin đã được cập nhật trước đó, cho phép người dùng chỉnh sửa các thông tin:

| **Thông tin** | **Kiểu** | **Bắt buộc** | **Mô tả** |
| --- | --- | --- | --- |
| Tên | Textbox | x   | \- Cho phép nhập tối đa 100 ký tự |
| --- | --- | --- | --- |
| Mã  | Textbox | x   | \- Cho phép nhâp tối đa 50 ký tự<br><br>\- Mã là giá trị duy nhất |
| --- | --- | --- | --- |
| Trạng thái | Selectbox | x   | \- Có 2 trạng thái:<br><br>\+ Hoạt động<br><br>\+ Không hoạt động<br><br>\- Mặc định: Hoạt động |
| --- | --- | --- | --- |
| Mô tả | Textarea |     | \- Cho phép nhập tối đa 500 ký tự |
| --- | --- | --- | --- |
| File đính kèm | File upload |     | \- Cho phép upload file ảnh: png, jpeg, png<br><br>\- Dung lượng tối đa: 25MB |
| --- | --- | --- | --- |
| Exclude from Visualization: | Checbox |     | \- Khi checked: tất cả tài sản thuộc nhóm tài sản này sẽ được thêm vào visualization<br><br>\- Unchecked: các tài sản thuộc nhóm tài sản này sẽ không được thêm vào visualization |
| --- | --- | --- | --- |
| Huỷ | Button |     | Hiển thị popup xác nhận Hủy lưu thông tin  <br>\- Hủy: Đóng popup xác nhận và popup chỉnh sửa, quay lại màn hình danh sách, không cập nhật CSDL  <br>\- Không hủy: Đóng popup xác nhận, giữ nguyên popup thêm mới với các thông tin dữ liệu người dùng đang nhập |
| --- | --- | --- | --- |
| Cập nhật | Button |     | Kiểm tra điều kiện:<br><br>\- Thỏa mãn: Đóng popup chỉnh sửa, cập nhật thông tin trong CSDL, hiển thị thông báo thành công cho người dùng<br><br>\- Không thỏa mãn: Thông báo lỗi người dùng |
| --- | --- | --- | --- |

- Xoá nhóm tài sản
- Chọn chức năng “Xoá”, hệ thống hiển thị popup xác nhận Xoá . Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác. Trường hợp người dùng Xác nhận, hệ thống xoá bản ghi khỏi CSDL.
- Chi tiết nhóm tài sản
- Người dùng click vào tên nhóm tài sản để xem chi tiết nhóm tài sản
- Chọn chức năng “Xem chi tiết”, hệ thống hiển thị cửa sổ thông tin chi tiết nhóm tài sản bao gồm:
    - - Tên
        - Mã
        - Trạng thái
        - Mô tả
        - File đính kèm
        - Đối tương liên quan:
            - Các tài sản: số lượng
            - Click vào số lượng hiển thị dánh sách tài sản

1.  Tiền điều kiện

- Người dùng login hệ thống dưới quyền quản trị hệ thống.

1.  Điều kiện rẽ nhánh

- Khi người dùng không nhập đầy đủ các thông tin bắt buộc, hệ thống hiển thị cảnh báo.

1.  Hậu điều kiện

Xem danh sách, chỉnh sửa , xoá thông tin nhóm tài sản và xem chi tiết nhóm tài sản

### Quản lý tài sản

1.  Mô tả nghiệp vụ

- Chức năng cho phép người dùng có vai trò quản lý danh sách tài sản có trong hệ thống
- Người dùng có thể thêm mới, chỉnh sửa, xoá thông tin tài sản, xem danh sách hoặc xem chi tiết tài sản

1.  Dòng sự kiện chính

- Người sử dụng chọn chức năng Tài sản -> Quản lý tài sản. Thông tin hiển thị tại danh sách tài sản bao gồm:
    - Tên (Click ra màn hình xem chi tiết)
    - Mã
    - Trạng thái
    - Địa điểm
    - Vị trí
    - Nhóm tài sản
    - Hãng sản xuất
    - Loại thiết bị
    - Người tạo
    - Thời gian tạo
    - Thời gian cập nhật
    - Thao tác: Xoá/ Sửa
- Màn hình danh sách tài sản
- Tại danh sách tài sản , sắp xếp theo thứ tự thời gian cập nhật mới nhất lên đầu tiên.
- Chức năng “Tìm kiếm”, nhập giá trị để tìm kiếm phiếu yêu cầu theo các tiêu chí:Tên, trạng thái, nhóm tài sản
- Chức năng “Configure Table”: cho phép người dùng lựa chọn các trường thông tin hiển thị ngoài màn hình danh sách
- Chức năng “Export excel”: cho phép người dùng export danh sách tài sản ra file excel
- Thêm mới tài sản

Chức năng “Thêm mới”: cho phép người dùng thực hiện thêm mới tài sản

<div class="joplin-table-wrapper"><table><thead><tr><th><p><strong>Thông tin</strong></p></th><th><p><strong>Kiểu</strong></p></th><th><p><strong>Bắt buộc</strong></p></th><th><p><strong>Mô tả</strong></p></th></tr><tr><th><p>Tên</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Mã</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhâp tối đa 50 ký tự</p><p>- Mã là giá trị duy nhất</p></th></tr><tr><th><p>Nhóm tài sản</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Danh sách nhóm tài sản được lấy từ danh mục nhóm tài sản có trạng thái “Hoạt động”</p></th></tr><tr><th><p>Trạng thái thiết bị</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Có các trạng thái:</p><p>+ Đang hoạt động</p><p>+ Dự phòng</p><p>+ Bảo trì</p><p>+ Hỏng</p><p>- Mặc định: Hoạt động</p></th></tr><tr><th><p>Mô tả</p></th><th><p>Textarea</p></th><th><p></p></th><th><p>- Cho phép nhập tối đa 500 ký tự</p></th></tr><tr><th><p>File đính kèm</p></th><th><p>File upload</p></th><th><p></p></th><th><p>- Cho phép upload file ảnh: png, jpeg, png</p><p>- Dung lượng tối đa: 25MB</p></th></tr><tr><th><p>Loại thiết bị</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Model</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Serial</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Hãng sản xuất</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Ngày lắp đặt</p></th><th><p>Datepicker</p></th><th><p></p></th><th><p>- Cho phép nhập/ chọn ngày lắp đặt</p><p>- Placeholder: DD/MM/YYYY</p></th></tr><tr><th><p>Ngày mua</p></th><th><p>Datepiecker</p></th><th><p></p></th><th><p>- Cho phép nhập/ chọn ngày lắp đặt</p><p>- Placeholder: DD/MM/YYYY</p></th></tr><tr><th><p>Thời hạn bảo hành</p></th><th><p>Textbox</p></th><th><p></p></th><th><p>- Thời hạn bảo hành của thiết bị (đơn vị : Tháng)</p><p>- Chỉ cho phép nhập số nguyên dương</p></th></tr><tr><th><p>Thời gian bảo hành</p></th><th><p>Datepicker</p></th><th><p></p></th><th><p>- Disable<br>- Thơi gian= Ngày mua + thời hạn bảo hành</p></th></tr><tr><th><p>Region</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách Region theo phân quyền của người tạo</p></th></tr><tr><th><p>Site</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách Site theo giá trị Region được chọn ở trên</p></th></tr><tr><th><p>Location</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách Location theo giá trị Site được chọn ở trên</p></th></tr><tr><th><p>Tạo mới</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình danh sách</li></ol></th></tr><tr><th><p>Tạo và thêm tiếp</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình thêm mới nhóm tài sản</li></ol></th></tr><tr><th><p>Huỷ</p></th><th><p>Button</p></th><th><p></p></th><th><p>- Hiển thị popup xác nhận Hủy lưu thông tin<br>+ Bấm Có: Đóng popup xác nhận và popup thêm mới, quay lại màn hình danh sách, không cập nhật CSDL, điều hướng người dùng về màn hình danh sách nhóm tài sản<br>+ Bấm Không: Đóng popup xác nhận, giữ nguyên popup Thêm mới/ chỉnh sửa với các thông tin dữ liệu người dùng đang nhập</p></th></tr></thead></table></div>

- Chỉnh sửa tài sản
- Chọn chức năng “Chỉnh sửa”, hệ thống hiển thị các thông tin đã được cập nhật trước đó, cho phép người dùng chỉnh sửa các thông tin:

| **Thông tin** | **Kiểu** | **Bắt buộc** | **Mô tả** |
| --- | --- | --- | --- |
| Tên | Textbox | x   | \- Cho phép nhập tối đa 100 ký tự |
| --- | --- | --- | --- |
| Mã  | Textbox | x   | \- Cho phép nhâp tối đa 50 ký tự<br><br>\- Mã là giá trị duy nhất |
| --- | --- | --- | --- |
| Nhóm tài sản | Selectbox | x   | \- Danh sách nhóm tài sản được lấy từ danh mục nhóm tài sản có trạng thái “Hoạt động” |
| --- | --- | --- | --- |
| Trạng thái | Selectbox | x   | \- Có các trạng thái:<br><br>\+ Đang hoạt động<br><br>\+ Dự phòng<br><br>\+ Bảo trì<br><br>\+ Hỏng<br><br>\- Mặc định: Hoạt động |
| --- | --- | --- | --- |
| Mô tả | Textarea |     | \- Cho phép nhập tối đa 500 ký tự |
| --- | --- | --- | --- |
| File đính kèm | File upload |     | \- Cho phép upload file ảnh: png, jpeg, png<br><br>\- Dung lượng tối đa: 25MB |
| --- | --- | --- | --- |
| Loại thiết bị | Textbox | x   | \- Cho phép nhập tối đa 100 ký tự |
| --- | --- | --- | --- |
| Model | Textbox |     |     |
| --- | --- | --- | --- |
| Serial | Textbox |     |     |
| --- | --- | --- | --- |
| Hãng sản xuất | Textbox |     |     |
| --- | --- | --- | --- |
| Ngày lắp đặt | Datepicker |     | \- Cho phép nhập/ chọn ngày lắp đặt<br><br>\- Placeholder: DD/MM/YYYY |
| --- | --- | --- | --- |
| Ngày mua | Datepiecker |     | \- Cho phép nhập/ chọn ngày lắp đặt<br><br>\- Placeholder: DD/MM/YYYY |
| --- | --- | --- | --- |
| Thời hạn bảo hành | Textbox |     | \- Thời hạn bảo hành của thiết bị (đơn vị : Tháng)<br><br>\- Chỉ cho phép nhập số nguyên dương |
| --- | --- | --- | --- |
| Thời gian bảo hành | Datepicker |     | \- Disable  <br>\- Thơi gian= Ngày mua + thời hạn bảo hành |
| --- | --- | --- | --- |
| Region | Selectbox |     | \- Hiển thị danh sách Region theo phân quyền của người tạo |
| --- | --- | --- | --- |
| Site | Selectbox |     | \- Hiển thị danh sách Site theo giá trị Region được chọn ở trên |
| --- | --- | --- | --- |
| Location | Selectbox |     | \- Hiển thị danh sách Location theo giá trị Site được chọn ở trên |
| --- | --- | --- | --- |
| Huỷ | Button |     | Hiển thị popup xác nhận Hủy lưu thông tin  <br>\- Hủy: Đóng popup xác nhận và popup chỉnh sửa, quay lại màn hình danh sách, không cập nhật CSDL  <br>\- Không hủy: Đóng popup xác nhận, giữ nguyên popup thêm mới với các thông tin dữ liệu người dùng đang nhập |
| --- | --- | --- | --- |
| Cập nhật | Button |     | Kiểm tra điều kiện:<br><br>\- Thỏa mãn: Đóng popup chỉnh sửa, cập nhật thông tin trong CSDL, hiển thị thông báo thành công cho người dùng<br><br>\- Không thỏa mãn: Thông báo lỗi người dùng |
| --- | --- | --- | --- |

- Xoá thông tin tài sản
- Chọn chức năng “Xoá”, hệ thống hiển thị popup xác nhận Xoá . Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác. Trường hợp người dùng Xác nhận, hệ thống xoá bản ghi khỏi CSDL.
- Chi tiết thông tin tài sản
- Người dùng click vào tên tài sản để xem chi tiết tài sản
- Chọn chức năng “Xem chi tiết”, hệ thống hiển thị cửa sổ thông tin chi tiết tài sản bao gồm:
    - - Tên
        - Mã
        - Trạng thái
        - Mô tả
        - File đính kèm
        - Đối tương liên quan:
            - Các tài sản: số lượng
            - Click vào số lượng hiển thị dánh sách tài sản

1.  Tiền điều kiện

- Người dùng login hệ thống dưới quyền quản trị hệ thống.

1.  Điều kiện rẽ nhánh

- Khi người dùng không nhập đầy đủ các thông tin bắt buộc, hệ thống hiển thị cảnh báo.

1.  Hậu điều kiện

Xem danh sách, chỉnh sửa , xoá thông tin tài sản.

### Quản lý Smart lock

1.  Mô tả nghiệp vụ

- Chức năng cho phép người dùng có vai trò quản lý danh sách smart lock có trong hệ thống
- Người dùng có thể thêm mới, chỉnh sửa, xoá thông tin smart lock, xem danh sách hoặc xem chi tiết smart lock.

1.  Dòng sự kiện chính

- Người sử dụng chọn chức năng Thiết bị an ninh vật lý -> Quản lý smart lock. Thông tin hiển thị tại danh sách smart lock bao gồm:
    - Tên (Click ra màn hình xem chi tiết)
    - Mã
    - Trạng thái
    - Địa điểm
    - Vị trí
    - Rack
    - Nhà sản xuất
    - Loại thiết bị
    - Người tạo
    - Thời gian tạo
    - Thời gian cập nhật
    - Thao tác: Xoá/ Sửa
- Màn hình danh sách smart lock
- Tại danh sách tài sản , sắp xếp theo thứ tự thời gian cập nhật mới nhất lên đầu tiên.
- Chức năng “Tìm kiếm”, nhập giá trị để tìm kiếm phiếu yêu cầu theo các tiêu chí:Tên, trạng thái, nhóm tài sản
- Chức năng “Configure Table”: cho phép người dùng lựa chọn các trường thông tin hiển thị ngoài màn hình danh sách
- Chức năng “Export excel”: cho phép người dùng export danh sách smart lock ra file excel
- Thêm mới smart lock

Chức năng “Thêm mới”: cho phép người dùng thực hiện thêm mới tài sản

<div class="joplin-table-wrapper"><table><thead><tr><th><p><strong>Thông tin</strong></p></th><th><p><strong>Kiểu</strong></p></th><th><p><strong>Bắt buộc</strong></p></th><th><p><strong>Mô tả</strong></p></th></tr><tr><th><p>Tên</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Mã</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhâp tối đa 50 ký tự</p><p>- Mã là giá trị duy nhất</p></th></tr><tr><th><p>Trạng thái</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Có các trạng thái:</p><p>+</p><p>+</p><p>- Mặc định: Hoạt động</p></th></tr><tr><th><p>Mô tả</p></th><th><p>Textarea</p></th><th><p></p></th><th><p>- Cho phép nhập tối đa 500 ký tự</p></th></tr><tr><th><p>File đính kèm</p></th><th><p>File upload</p></th><th><p></p></th><th><p>- Cho phép upload file ảnh: png, jpeg, png</p><p>- Dung lượng tối đa: 25MB</p></th></tr><tr><th><p>Loại thiết bị</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Model</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Serial</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Hãng sản xuất</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Ngày lắp đặt</p></th><th><p>Datepicker</p></th><th><p></p></th><th><p>- Cho phép nhập/ chọn ngày lắp đặt</p><p>- Placeholder: DD/MM/YYYY</p></th></tr><tr><th><p>Ngày mua</p></th><th><p>Datepiecker</p></th><th><p></p></th><th><p>- Cho phép nhập/ chọn ngày lắp đặt</p><p>- Placeholder: DD/MM/YYYY</p></th></tr><tr><th><p>Thời hạn bảo hành</p></th><th><p>Textbox</p></th><th><p></p></th><th><p>- Thời hạn bảo hành của thiết bị (đơn vị : Tháng)</p><p>- Chỉ cho phép nhập số nguyên dương</p></th></tr><tr><th><p>Thời gian bảo hành</p></th><th><p>Datepicker</p></th><th><p></p></th><th><p>- Disable<br>- Thơi gian= Ngày mua + thời hạn bảo hành</p></th></tr><tr><th><p>Site</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Hiển thị danh sách Site theo giá trị Region được chọn ở trên</p></th></tr><tr><th><p>Location</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Hiển thị danh sách Location theo giá trị Site được chọn ở trên</p></th></tr><tr><th><p>Rack</p></th><th><p>Selecbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách rack thuộc location đã chọn ở trên</p></th></tr><tr><th><p>Mặt rack</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Có các giá trị:</p><ul><li>Mặt trước</li><li>Mặt sau</li></ul></th></tr><tr><th><p>Tạo mới</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình danh sách</li></ol></th></tr><tr><th><p>Tạo và thêm tiếp</p></th><th><p>Button</p></th><th><p></p></th><th><ol><li>Kiểm tra các rằng buộc dữ liệu<br>- Thỏa mãn: Cập nhật vào CSDL<br>- Không thỏa mãn: Thông báo lỗi người dùng và không cập nhật thông tin vào CSDL</li><li>Sau lưu thành công hiển thị màn hình thêm mới smart lock</li></ol></th></tr><tr><th><p>Huỷ</p></th><th><p>Button</p></th><th><p></p></th><th><p>- Hiển thị popup xác nhận Hủy lưu thông tin<br>+ Bấm Có: Đóng popup xác nhận và popup thêm mới, quay lại màn hình danh sách, không cập nhật CSDL, điều hướng người dùng về màn hình danh sách smart lock<br>+ Bấm Không: Đóng popup xác nhận, giữ nguyên popup Thêm mới/ chỉnh sửa với các thông tin dữ liệu người dùng đang nhập</p></th></tr></thead></table></div>

- Chỉnh sửa smart lock
- Chọn chức năng “Chỉnh sửa”, hệ thống hiển thị các thông tin đã được cập nhật trước đó, cho phép người dùng chỉnh sửa các thông tin:

<div class="joplin-table-wrapper"><table><thead><tr><th><p><strong>Thông tin</strong></p></th><th><p><strong>Kiểu</strong></p></th><th><p><strong>Bắt buộc</strong></p></th><th><p><strong>Mô tả</strong></p></th></tr><tr><th><p>Tên</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Mã</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhâp tối đa 50 ký tự</p><p>- Mã là giá trị duy nhất</p></th></tr><tr><th><p>Trạng thái</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Có các trạng thái:</p><p>+</p><p>+</p><p>- Mặc định: Hoạt động</p></th></tr><tr><th><p>Mô tả</p></th><th><p>Textarea</p></th><th><p></p></th><th><p>- Cho phép nhập tối đa 500 ký tự</p></th></tr><tr><th><p>File đính kèm</p></th><th><p>File upload</p></th><th><p></p></th><th><p>- Cho phép upload file ảnh: png, jpeg, png</p><p>- Dung lượng tối đa: 25MB</p></th></tr><tr><th><p>Loại thiết bị</p></th><th><p>Textbox</p></th><th><p>x</p></th><th><p>- Cho phép nhập tối đa 100 ký tự</p></th></tr><tr><th><p>Model</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Serial</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Hãng sản xuất</p></th><th><p>Textbox</p></th><th><p></p></th><th><p></p></th></tr><tr><th><p>Ngày lắp đặt</p></th><th><p>Datepicker</p></th><th><p></p></th><th><p>- Cho phép nhập/ chọn ngày lắp đặt</p><p>- Placeholder: DD/MM/YYYY</p></th></tr><tr><th><p>Ngày mua</p></th><th><p>Datepiecker</p></th><th><p></p></th><th><p>- Cho phép nhập/ chọn ngày lắp đặt</p><p>- Placeholder: DD/MM/YYYY</p></th></tr><tr><th><p>Thời hạn bảo hành</p></th><th><p>Textbox</p></th><th><p></p></th><th><p>- Thời hạn bảo hành của thiết bị (đơn vị : Tháng)</p><p>- Chỉ cho phép nhập số nguyên dương</p></th></tr><tr><th><p>Thời gian bảo hành</p></th><th><p>Datepicker</p></th><th><p></p></th><th><p>- Disable<br>- Thơi gian= Ngày mua + thời hạn bảo hành</p></th></tr><tr><th><p>Site</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Hiển thị danh sách Site theo giá trị Region được chọn ở trên</p></th></tr><tr><th><p>Location</p></th><th><p>Selectbox</p></th><th><p>x</p></th><th><p>- Hiển thị danh sách Location theo giá trị Site được chọn ở trên</p></th></tr><tr><th><p>Rack</p></th><th><p>Selecbox</p></th><th><p></p></th><th><p>- Hiển thị danh sách rack thuộc location đã chọn ở trên</p></th></tr><tr><th><p>Mặt rack</p></th><th><p>Selectbox</p></th><th><p></p></th><th><p>- Có các giá trị:</p><ul><li>Mặt trước</li><li>Mặt sau</li></ul></th></tr><tr><th><p>Huỷ</p></th><th><p>Button</p></th><th><p></p></th><th><p>Hiển thị popup xác nhận Hủy lưu thông tin<br>- Hủy: Đóng popup xác nhận và popup chỉnh sửa, quay lại màn hình danh sách, không cập nhật CSDL<br>- Không hủy: Đóng popup xác nhận, giữ nguyên popup thêm mới với các thông tin dữ liệu người dùng đang nhập</p></th></tr><tr><th><p>Cập nhật</p></th><th><p>Button</p></th><th><p></p></th><th><p>Kiểm tra điều kiện:</p><p>- Thỏa mãn: Đóng popup chỉnh sửa, cập nhật thông tin trong CSDL, hiển thị thông báo thành công cho người dùng</p><p>- Không thỏa mãn: Thông báo lỗi người dùng</p></th></tr></thead></table></div>

- Xoá smart lock
- Chọn chức năng “Xoá”, hệ thống hiển thị popup xác nhận Xoá . Trường hợp người dùng chọn Huỷ, hệ thống huỷ thao tác. Trường hợp người dùng Xác nhận, hệ thống xoá bản ghi khỏi CSDL.
- Chi tiết smart lock
- Người dùng click vào tên smart lock để xem chi tiết
- Chọn chức năng “Xem chi tiết”, hệ thống hiển thị cửa sổ thông tin chi tiết smart bao gồm:
- Site
- Location
- Rack ( Mặt rack)
- Status
- Loại thiết bị
- Model
- Serial
- Hãng sản xuất
- Ngày lắp đặt
- Ngày mua
- Thời hạn bảo hành
- Thời gian bảo hành
- File đính kèm

1.  Tiền điều kiện

- Người dùng login hệ thống dưới quyền quản trị hệ thống.

1.  Điều kiện rẽ nhánh

- Khi người dùng không nhập đầy đủ các thông tin bắt buộc, hệ thống hiển thị cảnh báo.

1.  Hậu điều kiện

Xem danh sách, chỉnh sửa , xoá thông tin smart lock.