# NetBox SmartLock Plugin

Plugin NetBox để quản lý tài sản, thiết bị Smart Lock và quy trình phiếu yêu cầu ra/vào trung tâm dữ liệu. Repo này gồm plugin nghiệp vụ `netbox_smartlock`, plugin upload file dùng chung, và môi trường NetBox Docker phục vụ phát triển local.

## Cấu Trúc Repo

- `netbox_smartlock_plugin/`: mã nguồn plugin `netbox_smartlock`.
- `upload_file_plugin-production/`: plugin upload/đính kèm file ảnh dùng trong form NetBox.
- `netbox-docker/`: môi trường NetBox Docker Compose đã cấu hình để load hai plugin.

## Chức Năng Chính

### Tài Sản Và Thiết Bị

- Quản lý `Nhóm tài sản`.
- Quản lý `Tài sản` nghiệp vụ độc lập theo DCIM.md.
- Tài sản dùng các trường riêng cho nhóm tài sản, trạng thái, Site, Location, loại thiết bị, hãng sản xuất, serial và bảo hành.
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
- Hỗ trợ file ảnh theo DCIM.md: `jpg`, `jpeg`, `png`.
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

## Google SSO

SSO được cấu hình trực tiếp theo tài liệu chính thức của NetBox cho Google OAuth2:

- Google: https://netboxlabs.com/docs/netbox/administration/authentication/google/

Google Cloud OAuth client phải có redirect URI:

```text
http://localhost:8000/oauth/complete/google-oauth2/
```

Google không cho dùng IP thô cho OAuth redirect, trừ `127.0.0.1`. Khi dev local, dùng `localhost`; khi production, dùng domain HTTPS thật.

Cấu hình trong `netbox-docker/env/netbox.env`:

```env
REMOTE_AUTH_ENABLED=True
REMOTE_AUTH_AUTO_CREATE_USER=True
REMOTE_AUTH_BACKEND=social_core.backends.google.GoogleOAuth2
REMOTE_AUTH_DEFAULT_GROUPS=Guest
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=<google-client-id>
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE=openid email profile
SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_VERIFIED_EMAIL=True
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=
SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN=False
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_HOSTED_DOMAINS=
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS=prompt=select_account
CSRF_TRUSTED_ORIGINS=http://localhost:8000
LOGOUT_REDIRECT_URL=http://localhost:8000/login/
```

Scope `openid email profile` kích hoạt OpenID Connect trên Google OAuth2 và cho phép NetBox nhận thông tin định danh cơ bản của user.
Nếu dùng Google Workspace, cấu hình thêm domain:

```env
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=company.com
SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN=True
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_HOSTED_DOMAINS=company.com
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS=prompt=select_account hd=company.com
```

`hd=company.com` chỉ là hint trên màn Google; pipeline vẫn kiểm tra claim `email_verified`, domain email và `hd` ở backend.

OAuth client secret không được đặt trong `.env` thật. Đặt secret vào các file local đã bị Git ignore:

```text
netbox-docker/secrets/google_oauth2_secret.txt
```

Container sẽ mount file này thành Docker secret:

```text
/run/secrets/google_oauth2_secret
```

Google sẽ hiển thị trên màn `/login/` mặc định của NetBox. NetBox tạo hoặc liên kết user local sau khi đăng nhập SSO; user SSO mới được đưa vào group `Guest` mặc định. Quyền `Admin` phải được cấp thủ công trong NetBox bằng group và ObjectPermission.

Policy production:

- Chỉ cho phép email Google corporate đã xác minh đăng nhập NetBox.
- Không bật tự đồng bộ group từ Google nếu chưa có yêu cầu nghiệp vụ rõ; NetBox vẫn là nơi quản lý quyền bằng `Admin`, `Guest` và ObjectPermission.
- Luôn giữ local admin break-glass: không tắt login local của NetBox và luôn có ít nhất một superuser local để đăng nhập khi Google lỗi.

Bootstrap group/quyền SmartLock:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_bootstrap_rbac
```

Audit SSO và link thủ công local user với Google khi thật sự cần:

```powershell
cd netbox-docker
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_sso_audit
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_sso_link --username admin --confirm-username admin --provider google-oauth2 --uid <google-sub-claim>
```

Chỉ dùng `smartlock_sso_link` sau khi admin đã xác minh chắc chắn Google `sub` thuộc đúng người dùng local. Command không tự link theo email để tránh nâng quyền sai vào tài khoản admin.

Troubleshooting SSO:

- `Single sign-on failed`: xem log `docker compose logs netbox | Select-String "Google SSO login rejected"`.
- `duplicate_email_without_social_association`: email Google trùng local user nhưng chưa có social link. Dùng tài khoản Google khác, đổi email local user, hoặc link thủ công bằng `smartlock_sso_link`.
- `email_not_verified`: Google chưa xác minh email. Dùng account đã verified.
- `email_domain_rejected`: email không thuộc `SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS`.
- `hosted_domain_missing`: đang bật Workspace mode nhưng Google không trả claim `hd`.
- `hosted_domain_rejected`: claim `hd` không thuộc `SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_HOSTED_DOMAINS`.
- Token Google không được lưu trong `social_django_usersocialauth.extra_data`; pipeline chỉ giữ metadata không nhạy cảm cần thiết.

Sau khi bootstrap:

- group `Admin` có quyền quản trị AssetGroup, Asset, SmartLock và workflow phiếu yêu cầu;
- group `Guest` chỉ quản lý phiếu/person do chính user đó tạo;
- Region/Site/Location/Rack scope do ObjectPermission của NetBox quản lý;
- nếu cần giới hạn theo site/region cho từng khách hàng, thêm constraint trực tiếp vào ObjectPermission trong NetBox.

Production hardening:

- Dùng HTTPS public domain, ví dụ `https://netbox.example.com`.
- Cập nhật `ALLOWED_HOSTS`, `CORS_ORIGIN_WHITELIST`, `CSRF_TRUSTED_ORIGINS` và Google redirect URI theo domain thật.
- Bật `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`; chỉ bật `SECURE_HSTS_PRELOAD=True` khi domain đã sẵn sàng preload.
- Đổi toàn bộ secret dev: `SECRET_KEY`, `API_TOKEN_PEPPER_1`, database/Redis password và Google client secret.
- Ưu tiên Docker/Kubernetes secrets thay vì commit secret vào `.env`.

Kiểm tra nhanh cấu hình SSO trước khi chạy:

```powershell
cd netbox-docker
python check-sso-preflight.py
```

Kiểm tra production:

```powershell
cd netbox-docker
python check-sso-preflight.py --production --base-url https://netbox.example.com
```

Checklist Google Console:

- Chọn OAuth app type `Internal` nếu dùng Google Workspace.
- Authorized redirect URI dev: `http://localhost:8000/oauth/complete/google-oauth2/`.
- Authorized redirect URI production: `https://netbox.example.com/oauth/complete/google-oauth2/`.
- Không dùng raw IP cho redirect URI, trừ `127.0.0.1` khi dev.
- Production chỉ dùng HTTPS domain thật.

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
