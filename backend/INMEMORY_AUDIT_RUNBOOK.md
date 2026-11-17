# Audit In-Memory Read & Warm-up — 17/11/2026

## Kết quả và phạm vi

Đã rà soát cây backend, model/migration, repository/domain/use case, endpoint/schema,
Docker Compose, seed, test và cấu hình API Frontend. Không thay đổi auth,
dependencies, rate_limit hoặc audit_worker. Không có audit_worker trong cây hiện tại.

Kiểm chứng: compile Python thành công; pytest: **24 passed, 4 subtests passed**.
Các test dùng mock DB/Redis trong bộ nhớ; không thay thế kiểm thử tích hợp hoặc đo tải.
Sau audit đã reset local dev theo quyền người dùng: migration tới 3768f0350384,
seed thành công, PostgreSQL/Redis healthy. Backend /health, đăng nhập 20020000,
GET /api/courses/ và Frontend /, /login đều trả HTTP 200. Redis nạp 35 catalog,
35 counter và student state có TTL. Kết quả này kiểm chứng luồng local tuần tự;
không thay thế kiểm thử đồng thời hoặc benchmark.

## Đã đạt

| Hạng mục | Bằng chứng/kết luận |
|---|---|
| PostgreSQL/Redis | Compose dùng postgres:15, redis:7; cổng máy Windows 5433/6379; backend Docker dùng db:5432, redis:6379 |
| Kết nối local | session.py mặc định localhost:5433; redis_client.py mặc định localhost:6379/0, decode_responses=True |
| Redis key | catalog:ready là String "1"; catalog:class:{UUID} là JSON; slot:counter:{UUID} là chuỗi số nguyên Redis, đọc bằng int() |
| Catalog JSON | id, class_code, course_id, course_code, course_name, credits, course_type, room, lecturer, max_capacity, prereq_ids, schedules đầy đủ |
| Student JSON | cohort, major_id, passed_course_ids, taken_course_ids, enrolled_classes; UUID chuyển str; số ID môn/ngành giữ int; SETEX 1800 giây |
| Student enrollment JSON | class_id, course_id, credits, course_type, schedules; chỉ trạng thái enrolled |
| Inverted index | Set index:all_classes, index:day:{day}, index:type:{type}, index:major:{major}; môn chung vào mọi ngành |
| Session | JSON danh sách phiên chưa hủy, end_time >= now; kiểm tra thời gian đóng/mở và cohort trên RAM |
| Warm-up | create_session sau commit: reset slots True; cancel_session sau commit: False; catalog thiếu cờ kích hoạt lazy warm-up |
| BR1–BR5 | Session; tín chỉ <=25 theo domain hiện hành; đủ tiên quyết đã passed; tối đa 1 PE; trùng lịch cùng thứ và chung tiết |
| note | Học lại nếu có transcript bất kể passed/failed; ngược lại Học lần đầu |
| is_valid | Lớp đã enrolled được ưu tiên True; lớp khác kiểm tra cả còn chỗ và BR2–BR5 |
| API | Hai endpoint đọc giữ nguyên response_model; Pydantic lọc trường nội bộ course_id/prereq_ids; phân trang giữ items/total/page/size/pages/next/prev |

## Lỗi đã sửa

- requirements/venv thiếu pytest, pytest-asyncio, httpx: đã bổ sung và cài vào venv.
  Phiên bản kiểm tra: redis 8.1.0, pytest 9.2.0, pytest-asyncio 1.5.0, httpx 0.28.1.
- Thêm pytest.ini: pythonpath=., testpaths=tests, asyncio_mode=auto và loop scope function.
- Test cũ dùng constructor domain thiếu trường, mock API cũ, dependency override lan giữa
  test và kiểm tra route không tồn tại /logs/abnormal. Đã cập nhật test, cô lập override;
  bỏ assertion route không tồn tại, không thêm tính năng ngoài tài liệu để làm test xanh.
- SQLStudentRepository trước đây làm mất major_id khi chuyển model sang domain,
  khiến adapter phải SELECT thêm. Đã giữ major_id trong domain/repository, bỏ SELECT dư.
- Đăng ký/hủy trước đây không invalidation cache. Endpoint giờ commit SQL trước,
  rồi xóa student state, counter lớp và catalog:ready. Lần đọc tiếp warm-up bằng
  SETNX khôi phục counter từ DB. Test xác nhận commit lỗi không xóa cache.
- Xem lịch có enrollment nhưng catalog chưa sẵn sàng: bổ sung lazy warm-up.
- Catalog/counter thiếu trước đây bị bỏ qua âm thầm: trả HTTP 503; JSON hỏng, counter
  không phải số cũng trả 503; lỗi Redis trả 503 qua exception handler của ứng dụng.
- Redis client thêm timeout kết nối/lệnh 3 giây. Compose thêm healthcheck Redis và
  backend phụ thuộc Redis healthy; bỏ thuộc tính version lỗi thời.
- Compose trước đây chạy seed.py mỗi lần backend khởi động. Seed thực hiện TRUNCATE
  và tạo lại tài khoản/dữ liệu nên đã bỏ seed tự động; chỉ chạy bằng lệnh chủ động.
- Thêm .env.example cho local. Code dùng os.getenv; file .env chỉ được nạp khi chạy
  uvicorn --env-file hoặc khi tự xuất biến môi trường. Không có .env thật lúc audit.

## Vấn đề còn lại và giới hạn kiến trúc

1. **Lỗi mật khẩu volume cũ đã xử lý sau audit**: người dùng đã cấp quyền reset;
   đã chạy docker compose down -v rồi dựng db/redis mới. Backend/Frontend hiện chạy
   local, hai container hạ tầng healthy. Các bước khắc phục mật khẩu bên dưới được
   giữ làm hướng dẫn nếu tái sử dụng volume cũ về sau.
2. **Tài liệu tự mâu thuẫn**: Mục 1.2 dùng session:active_config dạng object có is_open,
   semester_code; Bước 1 dùng danh sách id/allowed_cohorts/start_time/end_time/is_cancelled.
   Producer/consumer hiện thống nhất theo **danh sách của Bước 1**, đúng yêu cầu triển khai
   trước đó. Chưa thể tuyên bố khớp hoàn toàn object của Mục 1.2; các nhóm cần dùng cùng contract.
3. **Nhiều học kỳ chưa được cô lập**: warm-up hiện nạp toàn bộ CourseClass như yêu cầu
   triển khai trước và code mẫu; repository Student cũng lấy mọi enrollment đang enrolled.
   Chưa lọc Semester.is_active dù lời mô tả Mục 3.1 nói học kỳ active. Không nên đưa dữ liệu
   nhiều học kỳ vào vận hành trước khi thống nhất scope key, chọn học kỳ active và migration
   dữ liệu cache với nhóm phụ trách write. Tương tự lịch sử học kỳ hiện còn hardcode 20241.
4. **Chưa có đồng bộ giao dịch SQL–Redis**: invalidation sau commit sửa luồng tuần tự,
   nhưng vẫn có cửa sổ race giữa concurrent warm-up/write hoặc Redis lỗi sau commit.
   HTTP 503 sau ghi có thể xảy ra khi SQL đã lưu; phải đọc lại trạng thái trước khi retry ghi.
   Cần outbox/versioning/khóa phối hợp cho bảo đảm đồng thời; chưa có trong thiết kế hiện tại.
5. **Không phải toàn HTTP request đều zero SQL**: get_current_student (Người 3) vẫn SELECT
   Student để xác thực. Cache miss sinh viên/warm-up chủ động vẫn cần SQL. Test xác nhận
   phần catalog đọc sau warm-up và student cache hit không query lại course_classes.
6. **TTL không thay thế invalidation**: các nguồn sửa transcript/student hoặc nhập dữ liệu
   ngoài endpoint đăng ký cũng phải xóa student:state; sau seed cần làm sạch cache cũ.
7. Warm-up vẫn dùng KEYS index:* theo mẫu, có thể chặn Redis khi keyspace lớn;
   chưa benchmark các mục tiêu <5ms/<0.5ms. SETNX giữ counter cũ theo contract; muốn
   đồng bộ lại sau nhập DB ngoài luồng phải reset chủ động trong môi trường kiểm thử.
8. BR2 hiện loại tín chỉ các môn PE đã enrolled khỏi tổng, rồi cộng tín chỉ môn đang xét.
   Đây là logic domain hiện hữu, không phải tổng mọi tín chỉ như cách hiểu thông thường.
9. Test cũ ngoài thư mục tests (test_e2e_api.py/test_concurrency.py) là script thủ công,
   còn assumption JSON dạng list/route đăng ký cũ. Không được xem chúng là bằng chứng đạt;
   pytest.ini chỉ tự thu thập thư mục tests. Dùng kịch bản API bên dưới.
10. Pydantic Config cũ và thư viện rate limit/TestClient còn cảnh báo deprecation;
    không đổi response schema và không sửa thư viện/phần Người 3 trong đợt này.

## Chạy trên Windows PowerShell

### 1. Bật Docker và kiểm tra dữ liệu kết nối

Mở Docker Desktop và chờ engine sẵn sàng. Từ PowerShell:

```powershell
Set-Location C:\Users\nguye\KTPM\course-registration
docker info
docker compose config --quiet
docker compose up -d db redis
docker compose ps
docker compose exec -T db pg_isready -U vnu_user -d course_registration
docker compose exec -T redis redis-cli PING
docker compose logs --tail 40 backend
```

Kỳ vọng Postgres healthy, Redis PONG. Workflow bên dưới chạy backend/frontend local.
Các container cũ đang chiếm cổng thì dừng chúng (không xóa volume):

```powershell
docker compose stop backend frontend
```

**Nếu gặp lại lỗi mật khẩu**: lấy mật khẩu thực tế của role vnu_user rồi đặt
DATABASE_URL đúng. POSTGRES_PASSWORD trong Compose không đổi mật khẩu role đã có
trên volume. Không dùng docker compose down -v để sửa lỗi này.

Nếu đây là DB phát triển của bạn và bạn chủ động muốn đồng bộ role về mật khẩu
dev trong Compose, lệnh sau thay đổi mật khẩu role (mọi client dùng role này phải cập nhật):

```powershell
docker compose exec -T db psql -U vnu_user -d course_registration -c "ALTER ROLE vnu_user WITH PASSWORD 'vnu_password';"
```

Lệnh trên cần quyền quản trị role qua kết nối nội bộ; nếu bị từ chối, dùng tài khoản
quản trị PostgreSQL thực tế. Dừng các bước migration/API nếu chưa sửa được kết nối.

### 2. Venv, migration và seed

```powershell
Set-Location C:\Users\nguye\KTPM\course-registration\backend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip show redis pytest pytest-asyncio httpx
$env:DATABASE_URL = 'postgresql+asyncpg://vnu_user:vnu_password@localhost:5433/course_registration'
$env:REDIS_URL = 'redis://localhost:6379/0'
$env:FRONTEND_URL = 'http://localhost:3000'
@'
import asyncio
from sqlalchemy import text
from src.infrastructure.database.session import engine

async def check():
    async with engine.connect() as connection:
        print((await connection.execute(text("SELECT 1"))).scalar())
    await engine.dispose()

asyncio.run(check())
'@ | python -
python -m alembic upgrade head
python -m alembic current
```

Chỉ chạy seed khi muốn **xóa dữ liệu DB phát triển hiện có và tạo lại mẫu**.
Seed tạo admin admin@vnu.edu.vn / 1, sinh viên 20020000 / 1,
học kỳ 20241, cohort QH-2020-I/CQ, phiên mở từ hôm qua đến 7 ngày sau lúc seed.
Số lớp/transcript được tạo ngẫu nhiên nên kết quả cụ thể có thể khác giữa các lần seed.

```powershell
python seed.py
```

Nếu dùng Redis DB 0 riêng cho dự án này, sau seed làm sạch DB cache đó để tránh UUID
và catalog cũ (không chạy nếu DB 0 đang được ứng dụng khác dùng chung):

```powershell
docker compose -f ..\docker-compose.yml exec -T redis redis-cli -n 0 FLUSHDB
```

### 3. Chạy pytest

Tại backend với venv đã kích hoạt:

```powershell
python -m pytest tests/test_inmemory_read.py tests/use_cases/test_cache_warmup.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
```

Hai file tập trung kiểm tra warm-up/read, JSON, flags, SQL-free cache hit,
invalidation sau commit và counter hỏng; bộ đầy đủ audit đạt 24 tests.
Tùy chọn no:cacheprovider tránh lỗi ghi .pytest_cache đang có trong workspace Windows.

### 4. Chạy backend local

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Giữ cửa sổ này chạy. Swagger: http://127.0.0.1:8000/docs.
Nếu dùng .env thay cho biến môi trường: sao chép .env.example thành .env, điều chỉnh
URL rồi thêm --env-file .env vào lệnh uvicorn. Biến môi trường đã xuất có ưu tiên.

### 5. Chạy frontend trong PowerShell thứ hai

```powershell
Set-Location C:\Users\nguye\KTPM\course-registration\frontend
node --version
pnpm --version
pnpm install --frozen-lockfile
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8000'
pnpm dev
```

package.json chỉ định pnpm 11.16.0. Nếu chưa có pnpm, cài bằng npm của Node:

```powershell
npm install --global pnpm@11.16.0
```

Mở http://localhost:3000 và đăng nhập tài khoản seed.
Giá trị API URL ở đây không có /api vì các trang đã tự nối /api/....

### 6. Test API trong PowerShell thứ ba

```powershell
Set-Location C:\Users\nguye\KTPM\course-registration
$api = 'http://127.0.0.1:8000'
Invoke-RestMethod "$api/health"
$login = Invoke-RestMethod -Method Post -Uri "$api/api/auth/login" -ContentType 'application/x-www-form-urlencoded' -Body @{username='20020000'; password='1'}
$headers = @{Authorization="Bearer $($login.access_token)"}
$courses = Invoke-RestMethod -Uri "$api/api/courses/?page=1&size=100" -Headers $headers
$courses | ConvertTo-Json -Depth 8
$filtered = Invoke-RestMethod -Uri "$api/api/courses/?day_of_week=2&course_type=normal&page=1&size=100" -Headers $headers
$filtered.items | Select-Object class_code,course_type,current_capacity,max_capacity,is_valid,note
Invoke-RestMethod -Uri "$api/api/courses/my-schedule" -Headers $headers
```

Kỳ vọng response danh sách có items, total, page, size, pages, next, prev.
Mỗi item có note/is_valid và schedules đúng filter; chưa đăng ký thì lịch là [].
Cache hit không truy vấn lại catalog SQL được kiểm tra bằng pytest, không suy ra
điều này chỉ từ HTTP 200. Xác thực thực tế vẫn truy vấn Student như lưu ý phía trên.

Tạo phiên qua admin để kiểm tra hook warm-up, dùng cohort đúng với seed:

```powershell
$adminLogin = Invoke-RestMethod -Method Post -Uri "$api/api/auth/login" -ContentType 'application/x-www-form-urlencoded' -Body @{username='admin@vnu.edu.vn'; password='1'}
$adminHeaders = @{Authorization="Bearer $($adminLogin.access_token)"}
$sessionBody = @{semester_code='20241'; start_time=(Get-Date).AddMinutes(-1).ToString('yyyy-MM-ddTHH:mm:ss'); end_time=(Get-Date).AddHours(2).ToString('yyyy-MM-ddTHH:mm:ss'); allowed_cohorts=@('QH-2020-I/CQ')} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$api/api/admin/sessions" -Headers $adminHeaders -ContentType 'application/json' -Body $sessionBody
```

Để kiểm tra hủy phiên, tạo thêm phiên tương lai, lấy ID từ GET /api/admin/sessions
rồi DELETE /api/admin/sessions/{id}. Service hiện cấm hủy phiên đang chạy/đã kết thúc.
Swagger: Authorize dùng username/password seed; chọn tài khoản admin khi gọi admin.

Đăng ký một lớp hợp lệ rồi xem lịch, sau đó hủy và xem lại:

```powershell
$courses = Invoke-RestMethod -Uri "$api/api/courses/?can_register=true&size=100" -Headers $headers
$chosen = $courses.items | Where-Object is_valid | Select-Object -First 1
if ($null -eq $chosen) { throw 'Không có lớp hợp lệ trong dữ liệu seed hiện tại' }
$body = @{course_class_id=$chosen.id} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$api/api/courses/register" -Headers $headers -ContentType 'application/json' -Body $body
Invoke-RestMethod -Uri "$api/api/courses/my-schedule" -Headers $headers
Invoke-RestMethod -Method Delete -Uri "$api/api/courses/register/$($chosen.id)" -Headers $headers
Invoke-RestMethod -Uri "$api/api/courses/my-schedule" -Headers $headers
```

### 7. Kiểm tra Redis sau GET hoặc mở phiên

```powershell
docker compose exec -T redis redis-cli GET catalog:ready
docker compose exec -T redis redis-cli --scan --pattern 'catalog:class:*'
docker compose exec -T redis redis-cli --scan --pattern 'slot:counter:*'
docker compose exec -T redis redis-cli --scan --pattern 'index:*'
docker compose exec -T redis redis-cli TYPE index:all_classes
docker compose exec -T redis redis-cli SCARD index:all_classes
docker compose exec -T redis redis-cli SINTER index:day:2 index:type:normal
docker compose exec -T redis redis-cli GET session:active_config
$classKey = docker compose exec -T redis redis-cli --scan --pattern 'catalog:class:*' | Select-Object -First 1
docker compose exec -T redis redis-cli GET $classKey
$studentKey = docker compose exec -T redis redis-cli --scan --pattern 'student:state:*' | Select-Object -First 1
docker compose exec -T redis redis-cli GET $studentKey
docker compose exec -T redis redis-cli TTL $studentKey
```

Kỳ vọng catalog:ready=1; index là set; session là JSON list; TTL student trong
khoảng 1..1800 nếu vừa đọc. -2 nghĩa key hết hạn/chưa tạo; -1 nghĩa thiếu TTL.
SINTER ở trên chưa lọc ngành; API còn giao thêm index:major:{major_id}.
Để thử lazy warm-up, chỉ xóa cờ rồi gọi lại GET courses (không xóa counter):

```powershell
docker compose exec -T redis redis-cli DEL catalog:ready
Invoke-RestMethod -Uri "$api/api/courses/?day_of_week=2&course_type=normal" -Headers $headers
docker compose exec -T redis redis-cli GET catalog:ready
```

Lần warm-up này dùng SETNX nên không ghi đè sĩ số đã có. Tránh chạy lại toàn bộ
Compose backend/frontend cùng lúc với hai tiến trình local vì trùng cổng 8000/3000.
