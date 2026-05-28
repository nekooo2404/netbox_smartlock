# NetBox SmartLock Plugin

Plugin NetBox để quản lý thiết bị Smart Lock và quy trình phiếu yêu cầu ra/vào trong môi trường DCIM.

## Cấu Trúc Repo

- `netbox_smartlock_plugin/`: mã nguồn plugin `netbox_smartlock`.
- `upload_file_plugin-production/`: plugin hỗ trợ upload/đính kèm file.
- `netbox-docker/`: môi trường NetBox chạy bằng Docker Compose, đã cấu hình để load plugin.

## Chức Năng Chính

### Smart Locks

- Quản lý danh sách Smart Lock.
- Xem chi tiết Smart Lock.
- Thêm, sửa, xóa Smart Lock bằng UI chuẩn của NetBox.
- Lọc theo thông tin thiết bị và vị trí DCIM.
- Hỗ trợ `Configure Table`.
- Hỗ trợ export mặc định của NetBox.
- Hỗ trợ `Export Excel (.xlsx)`.
- Quản lý thông tin liên quan như Asset Group, Region, Site, Location, Rack.
- Hỗ trợ file đính kèm qua upload plugin.

### Phiếu Yêu Cầu Ra/Vào

- Guest User tạo, sửa, xóa, gửi phiếu yêu cầu.
- Guest User quản lý danh sách đối tượng/người ra vào trong từng phiếu.
- Mỗi đối tượng yêu cầu file đính kèm.
- Hỗ trợ import đối tượng theo phạm vi từng phiếu.
- Admin xác nhận phiếu, xác minh đối tượng hợp lệ/không hợp lệ.
- Admin chấp nhận hoặc từ chối phiếu.
- Admin thực hiện check-in/check-out sau khi phiếu được chấp nhận.
- Hỗ trợ lịch sử xử lý, changelog và export Excel.
- Tái sử dụng Region, Site, Location, object permission, table, form, generic view và UI chuẩn của NetBox.

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
git clone <your-repo-url>
cd netbox_smartlock
```

### 2. Chuẩn Bị File Môi Trường

Repo dùng thư mục `netbox-docker/env/` để nạp biến môi trường cho Docker Compose.

Nếu chưa có file `.env` thật, tạo từ các file mẫu:

```powershell
copy netbox-docker\env\netbox.env.example netbox-docker\env\netbox.env
copy netbox-docker\env\postgres.env.example netbox-docker\env\postgres.env
copy netbox-docker\env\redis.env.example netbox-docker\env\redis.env
copy netbox-docker\env\redis-cache.env.example netbox-docker\env\redis-cache.env
```

Sau đó chỉnh `SECRET_KEY`, mật khẩu database, Redis và các thông tin môi trường theo máy local.

Không commit các file `.env` thật trong `netbox-docker/env/` vì chúng chứa secret. Chỉ commit các file `*.env.example`.

## Cấu Hình Postgres

Với môi trường Docker Compose trong repo, NetBox container kết nối Postgres qua service name nội bộ `postgres`.

File `netbox-docker/env/netbox.env` nên có cấu hình:

```env
DB_HOST=postgres
DB_NAME=netbox
DB_USER=postgres
DB_PASSWORD=<your-postgres-password>
DB_PORT=5432
```

File `netbox-docker/env/postgres.env` nên có cấu hình:

```env
POSTGRES_DB=netbox
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-postgres-password>
```

Trong `netbox-docker/docker-compose.yml`, Postgres có thể được expose ra máy host bằng port do từng người dùng tự chọn:

```yaml
ports:
  - "<your-postgres-host-port>:5432"
```

Ý nghĩa:

- NetBox container kết nối Postgres bằng `DB_HOST=postgres` và `DB_PORT=5432`.
- Công cụ chạy ngoài Docker như DBeaver, pgAdmin hoặc script local kết nối bằng `localhost:<your-postgres-host-port>`.
- Không đổi `DB_PORT` trong `netbox.env` sang host port này khi NetBox chạy cùng Docker Compose với Postgres.
- Ví dụ trên một máy cá nhân có thể dùng `"2404:5432"`, nhưng đây chỉ là host port local của người dùng đó.

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

## Chạy Migration

Chạy migration NetBox và plugin:

```powershell
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py migrate
```

Hoặc chỉ xem migration của plugin:

```powershell
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py showmigrations netbox_smartlock
```

## Tạo Superuser

```powershell
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py createsuperuser
```

## Kiểm Tra Sau Khi Chạy

Sau khi đăng nhập NetBox:

- menu `SmartLock` xuất hiện trên thanh điều hướng;
- mục `Smart Locks` mở được danh sách thiết bị;
- danh sách Smart Lock hỗ trợ `Configure Table`, import, export và `Export Excel`;
- click vào tên Smart Lock mở được trang chi tiết;
- mục `Access Requests` xuất hiện dưới nhóm `Security Control`;
- Guest User có thể tạo phiếu yêu cầu và thêm đối tượng có file đính kèm;
- Admin có thể xác nhận, verify, accept/reject, check-in/check-out và complete phiếu.

## Phát Triển Local

Source plugin được mount vào container qua `docker-compose.override.yml`.

Sau khi sửa code Python hoặc template, thường chỉ cần restart:

```powershell
cd netbox-docker
docker compose restart netbox netbox-worker
```

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

Chạy riêng test workflow phiếu yêu cầu:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_smartlock.tests.test_access_requests --keepdb
```

Xem log container:

```powershell
cd netbox-docker
docker compose logs -f netbox
```

## Ghi Chú Git

Các file `.env` thật đã được ignore để tránh commit secret:

- `netbox-docker/env/netbox.env`
- `netbox-docker/env/postgres.env`
- `netbox-docker/env/redis.env`
- `netbox-docker/env/redis-cache.env`

Chỉ các file mẫu `*.env.example` nên được đưa lên Git.
