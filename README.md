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

## Keycloak SSO Local

Repo co san overlay `netbox-docker/docker-compose.keycloak.yml` de chay Keycloak lam IAM hub cho moi truong dev.
Mo hinh local la LDAP -> Keycloak -> OIDC -> NetBox. NetBox khong ket noi LDAP truc tiep.

Overlay nay import realm `netbox-dev`, client OIDC `netbox-dev`, role `dcim-admin`/`dcim-guest`, group Keycloak `Admin`/`Guest`, va claim scope `dcim_regions`/`dcim_sites` de map xuong NetBox.
LDAP dev service seed user noi bo `ldap-admin`/`ldap-guest`, group LDAP `dcim-admin`/`dcim-guest`, va scope mau `region-1`/`site-1`. Day la nguon user noi bo chuan; NetBox khong dang nhap truc tiep LDAP va khong can user local trong Keycloak cho app.

Chay NetBox kem Keycloak:

```powershell
cd netbox-docker
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.keycloak.yml up -d --build
```

Ap cau hinh LDAP federation, role/group mapper va sync LDAP vao Keycloak:

```powershell
cd netbox-docker
powershell -ExecutionPolicy Bypass -File .\keycloak\configure-ldap-oidc.ps1
```

Bootstrap NetBox RBAC cho group `Admin`/`Guest` duoc sync tu Keycloak:

```powershell
cd netbox-docker
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.keycloak.yml exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_bootstrap_rbac
```

Keycloak Admin Console:

```text
http://keycloak.localtest.me:8080
```

Tai khoan dev mac dinh:

```text
admin / admin
```

User dang nhap NetBox mau di qua LDAP -> Keycloak -> OIDC:

```text
ldap-admin / admin
ldap-guest / guest
```

NetBox:

```text
http://localhost:8000
```

Cau hinh OIDC duoc khai bao trong `netbox-docker/env/netbox.env.example`.
Voi realm import mac dinh, client secret dev la:

```text
netbox-dev-secret
```

Neu tao lai client secret trong Keycloak, cap nhat bien nay trong `netbox-docker/env/netbox.env`:

```env
SOCIAL_AUTH_OIDC_SECRET=<client-secret-moi>
```

OAuth cua NetBox duoc cau hinh theo dung mau docs Google va Okta-style OIDC.
Google la backend truc tiep cua NetBox, nen Google Cloud OAuth client phai co
redirect URI:

```text
http://localhost:8000/oauth/complete/google-oauth2/
http://netbox.localtest.me:8000/oauth/complete/google-oauth2/
```

Keycloak dong vai tro OIDC provider giong cach docs Okta tao OIDC app. Callback
URL cua NetBox trong Keycloak phai gom:

```text
http://localhost:8000/oauth/complete/oidc/
http://netbox.localtest.me:8000/oauth/complete/oidc/
http://localhost:8000/oauth/disconnect/oidc/
http://netbox.localtest.me:8000/oauth/disconnect/oidc/
```

Hai backend nay cung hien tren man `/login/` mac dinh cua NetBox:

```env
REMOTE_AUTH_BACKEND=social_core.backends.google.GoogleOAuth2 social_core.backends.open_id_connect.OpenIdConnectAuth
```

Google direct login khong co claim Keycloak `groups`, `dcim_regions`,
`dcim_sites`; pipeline sync group/scope chi chay cho backend `oidc`.

De kiem tra NetBox container doc duoc discovery endpoint cua Keycloak:

```powershell
cd netbox-docker
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.keycloak.yml exec netbox curl http://keycloak.localtest.me:8080/realms/netbox-dev/.well-known/openid-configuration
```

Kiem tra end-to-end LDAP -> Keycloak -> OIDC -> NetBox API cho `ldap-admin` va `ldap-guest`:

```powershell
python netbox-docker\keycloak\verify_ldap_oidc_flow.py
```

Luu y phan quyen: plugin SmartLock dang dung group NetBox ten `Admin` cho cac thao tac quan tri phieu va danh muc tai san/Smart Lock; group `Guest` cho nguoi dung khach/doi tac.
Keycloak la noi map role/group. NetBox chi doc JWT OIDC claim `groups`/`roles` qua pipeline `netbox_smartlock.auth_pipeline.sync_keycloak_groups` va tu dong dong bo cac group trong allow-list:

```env
KEYCLOAK_GROUP_SYNC_ENABLED=True
KEYCLOAK_GROUP_SYNC_GROUPS=Admin Guest
KEYCLOAK_GROUP_SYNC_REMOVE=True
KEYCLOAK_GROUP_SYNC_GROUP_MAP=dcim-admin=Admin dcim-guest=Guest
KEYCLOAK_GROUP_SYNC_ROLE_MAP=dcim-admin=Admin dcim-guest=Guest
KEYCLOAK_SCOPE_SYNC_ENABLED=True
KEYCLOAK_SCOPE_SYNC_REGION_CLAIM=dcim_regions
KEYCLOAK_SCOPE_SYNC_SITE_CLAIM=dcim_sites
```

Pipeline chi quan ly cac group nam trong `KEYCLOAK_GROUP_SYNC_GROUPS`; cac group NetBox local khac duoc giu nguyen. Neu token/userinfo khong co claim `groups` hoac `roles`, pipeline bo qua sync de tranh xoa nham quyen.

Region/Site scope duoc quan ly tu Keycloak bang claim:

```json
{
  "dcim_regions": ["region-1"],
  "dcim_sites": ["site-1"]
}
```

Khi user login OIDC hoac goi plugin API bang Keycloak JWT, pipeline tao/cap nhat ObjectPermission rieng cho user voi prefix `SmartLock Keycloak Scope`. NetBox van enforce quyen bang `.restrict(user, "view")`, nen UI/API chi thay Region/Site/Location/Rack/Device va object SmartLock nam trong scope claim. Neu claim scope bi thieu, pipeline giu nguyen permission hien co de tranh tu khoa do mapper loi; neu claim co nhung rong, permission scope cu bi xoa.

Plugin API SmartLock nhan Bearer JWT tu Keycloak tren cac endpoint `/api/plugins/smartlock/...`; token phai co issuer realm `netbox-dev` va client `netbox-dev`.

Khi `KEYCLOAK_SCOPE_SYNC_ENABLED=True`, command `smartlock_bootstrap_rbac` chi tao RBAC group nen va khong cap quyen DCIM rong cho `Admin`/`Guest`; quyen Region/Site den tu Keycloak claim. Khi tat scope sync, command quay ve cach cu va cap scope mac dinh trong NetBox.

Production hardening:

- Dung domain HTTPS thong nhat, vi du `https://netbox.example.com` va `https://sso.example.com`; cap nhat `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, callback URL Keycloak, `SOCIAL_AUTH_OIDC_OIDC_ENDPOINT`, va `LOGOUT_REDIRECT_URL`.
- Bat `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`; chi bat `SECURE_HSTS_PRELOAD=True` khi domain san sang preload.
- Doi tat ca secret dev: `SECRET_KEY`, `API_TOKEN_PEPPER_1`, database/Redis password, `SOCIAL_AUTH_OIDC_SECRET`, Keycloak admin password, LDAP bind password. Uu tien Docker/Kubernetes secrets thay vi commit vao `.env`.
- Dung LDAPS tu Keycloak den LDAP: `KEYCLOAK_LDAP_CONNECTION_URL=ldaps://ldap.example.com:636` va `KEYCLOAK_LDAP_USE_TRUSTSTORE_SPI=always`.
- Giu man `/login/` mac dinh cua NetBox khi lam theo docs OAuth chinh thuc. Nut OAuth provider hien canh form local login; khong dung `break_glass=1`.

Neu database dev da tung dang nhap OIDC truoc khi cau hinh on dinh, co the co user trung email. Kiem tra association OIDC:

```powershell
cd netbox-docker
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.keycloak.yml exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py shell -c "from social_django.models import UserSocialAuth; print(list(UserSocialAuth.objects.values_list('provider','uid','user__username','user__email')))"
```

Group se duoc sync vao user dang duoc association OIDC tro den, khong nhat thiet la user local cung email tao thu cong tu truoc.

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
