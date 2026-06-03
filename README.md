# NetBox SmartLock Plugin

Plugin NetBox để quản lý tài sản, thiết bị Smart Lock và quy trình phiếu yêu cầu ra/vào trung tâm dữ liệu. Repo này gồm plugin nghiệp vụ `netbox_smartlock`, plugin upload file dùng chung, và môi trường NetBox Docker phục vụ phát triển local.

## Cấu Trúc Repo

- `netbox_smartlock_plugin/`: mã nguồn plugin `netbox_smartlock`.
- `upload_file_plugin-production/`: plugin upload/đính kèm file ảnh dùng trong form NetBox.
- `netbox-docker/`: môi trường NetBox Docker Compose đã cấu hình để load hai plugin.

## Chức Năng Chính

### Tài Sản Và Thiết Bị

- Quản lý `Nhóm tài sản`.
- Quản lý `Tài sản` liên kết với `Device` của NetBox.
- Tài sản dùng dữ liệu NetBox cho Site, Location, Rack, loại thiết bị, hãng sản xuất, serial và asset tag.
- Hỗ trợ lọc, tìm kiếm, `Configure Table`, import/export CSV mặc định của NetBox và export Excel.
- Hỗ trợ file đính kèm qua upload plugin.

### Smart Lock

- Quản lý danh sách Smart Lock.
- Xem chi tiết, thêm, sửa, xóa Smart Lock.
- Lọc theo thông tin thiết bị, nhóm tài sản và vị trí.
- Tự đồng bộ Region/Site/Location từ Rack/Location/Site khi có dữ liệu liên quan.
- Hỗ trợ file đính kèm, changelog, import/export CSV và export Excel.

### Phiếu Yêu Cầu Ra/Vào

- Guest User tạo, sửa, xóa và gửi phiếu yêu cầu.
- Guest User quản lý danh sách đối tượng/người ra vào trong từng phiếu.
- Mỗi đối tượng vào ra bắt buộc có file định danh đính kèm.
- Admin xác nhận phiếu, xác minh đối tượng hợp lệ/không hợp lệ.
- Admin chấp nhận hoặc từ chối phiếu.
- Admin thực hiện In/Out và hoàn thành phiếu sau khi phiếu được chấp nhận.
- Hỗ trợ lịch sử xử lý, changelog và export Excel.

### Upload File

- Widget upload dùng giao diện tiếng Việt thống nhất với plugin.
- Hỗ trợ kéo thả hoặc chọn file.
- Hỗ trợ ảnh: `jpg`, `jpeg`, `png`, `gif`, `webp`, `bmp`.
- Giới hạn dung lượng: `25MB` mỗi file.
- File được upload tạm thời và chỉ gắn vào đối tượng sau khi form chính được lưu.

## Yêu Cầu

- Docker
- Docker Compose
- Git
- NetBox `4.6.x`

## Tương Thích

- Plugin hiện được pin để chạy với NetBox `4.6.x`.
- Môi trường Docker trong repo dùng `netbox-docker` release `5.0.1`.
- Nếu đổi phiên bản NetBox, cần chạy lại test plugin trước khi deploy.

## Thiết Lập Môi Trường

### 1. Clone Source

```powershell
git clone https://github.com/nekooo2404/netbox_smartlock.git
cd netbox_smartlock
```

### 2. Chuẩn Bị File Môi Trường

Repo dùng thư mục `netbox-docker/env/` để nạp biến môi trường cho Docker Compose. Nếu chưa có file môi trường thật, tạo từ file mẫu:

```powershell
copy netbox-docker\env\netbox.env.example netbox-docker\env\netbox.env
copy netbox-docker\env\postgres.env.example netbox-docker\env\postgres.env
copy netbox-docker\env\redis.env.example netbox-docker\env\redis.env
copy netbox-docker\env\redis-cache.env.example netbox-docker\env\redis-cache.env
```

Sau đó chỉnh `SECRET_KEY`, mật khẩu database, Redis và các thông tin môi trường theo máy local.

Không commit các file `.env` thật trong `netbox-docker/env/` vì chúng chứa secret. Chỉ commit các file `*.env.example`.

## Cấu Hình Database Và Redis

NetBox container kết nối Postgres qua service name nội bộ `postgres`.

File `netbox-docker/env/netbox.env` nên có:

```env
DB_HOST=postgres
DB_NAME=netbox
DB_USER=postgres
DB_PASSWORD=<your-postgres-password>
DB_PORT=5432
```

File `netbox-docker/env/postgres.env` nên có:

```env
POSTGRES_DB=netbox
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-postgres-password>
```

Redis và Redis cache phải chạy cùng NetBox. Nếu `/login/` trả `500` với lỗi kết nối `redis-cache:6379`, kiểm tra và khởi động lại Redis:

```powershell
cd netbox-docker
docker compose up -d redis redis-cache
docker compose restart netbox netbox-worker
```

Postgres có thể expose ra máy host bằng port local do từng người dùng chọn:

```yaml
ports:
  - "<your-postgres-host-port>:5432"
```

NetBox container vẫn dùng `DB_HOST=postgres` và `DB_PORT=5432`. Công cụ ngoài Docker như DBeaver hoặc pgAdmin kết nối bằng `localhost:<your-postgres-host-port>`.

## Chạy NetBox Và Plugin

File `netbox-docker/docker-compose.override.yml` dùng để:

- build image custom từ `netbox-docker/Dockerfile.plugin`;
- cài `upload_file_plugin` và `netbox_smartlock` vào NetBox;
- mount source plugin vào container để phục vụ development local.

Chạy NetBox:

```powershell
cd netbox-docker
docker compose up -d --build
```

NetBox mặc định chạy tại:

```text
http://localhost:8000
```

## Migration

Chạy migration NetBox và plugin:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py migrate
```

Xem migration của plugin:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py showmigrations netbox_smartlock
```

## Tạo Superuser

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py createsuperuser
```

## Kiểm Tra Sau Khi Chạy

Sau khi đăng nhập NetBox:

- menu `SmartLock` xuất hiện trên thanh điều hướng;
- mục `Quản lý tài sản` mở được danh sách tài sản;
- trường thiết bị trên form/bảng/chi tiết tài sản hiển thị là `Thiết bị`;
- mục `Quản lý nhóm tài sản` mở được danh sách nhóm tài sản;
- mục `Quản lý smart lock` mở được danh sách Smart Lock;
- danh sách hỗ trợ `Configure Table`, import, export và `Export Excel`;
- form có upload file hiển thị tiếng Việt và upload được ảnh hợp lệ;
- Guest User có thể tạo phiếu yêu cầu và thêm đối tượng có file đính kèm;
- Admin có thể xác nhận, verify, accept/reject, In/Out và hoàn thành phiếu.

## Phát Triển Local

Source plugin được bind-mount vào container qua `docker-compose.override.yml`.

Sau khi sửa code Python, template hoặc JS static:

```powershell
cd netbox-docker
docker compose restart netbox netbox-worker
```

Nếu browser vẫn hiển thị JS/upload widget cũ, hard refresh trang vì file static có thể bị cache.

Nếu thay đổi dependency Python hoặc Dockerfile, build lại image:

```powershell
cd netbox-docker
docker compose up -d --build
```

Ví dụ dependency như `openpyxl` cần build lại image trước khi dùng tính năng export Excel.

## Lệnh Hữu Ích

Kiểm tra cấu hình Django/NetBox:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py check
```

Chạy toàn bộ test plugin:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_smartlock --keepdb
```

Chạy riêng test phiếu yêu cầu:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_smartlock.tests.test_access_requests --keepdb
```

Chạy riêng test tích hợp tài sản/SmartLock:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_smartlock.tests.test_integration --keepdb
```

Xem log container:

```powershell
cd netbox-docker
docker compose logs -f netbox
```

Kiểm tra trạng thái container:

```powershell
cd netbox-docker
docker compose ps
```

## Ghi Chú Git

Các file `.env` thật đã được ignore để tránh commit secret:

- `netbox-docker/env/netbox.env`
- `netbox-docker/env/postgres.env`
- `netbox-docker/env/redis.env`
- `netbox-docker/env/redis-cache.env`

Chỉ các file mẫu `*.env.example` nên được đưa lên Git.

Không commit dữ liệu phân tích local, log, export Excel/CSV cá nhân, media runtime hoặc file cache sinh ra trong quá trình chạy Docker.
