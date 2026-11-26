# Day 14 — Mission Answers

Các phần được ghi theo thứ tự bài lab. Số đo và mã HTTP dưới đây lấy từ các lần
chạy thực tế; các mục chưa chạy sẽ được đánh dấu rõ.

## Part 1 — Localhost vs Production

### Exercise 1.1 — Anti-patterns trong bản develop

| Vấn đề | Dòng trong `01-localhost-vs-production/develop/app.py` | Hậu quả |
|---|---:|---|
| API key và URL database có mật khẩu nằm trong code | 17–18 | Push repo public làm lộ credential; khó xoay vòng key. |
| `DEBUG` và `MAX_TOKENS` cố định | 21–22 | Không đổi cấu hình theo môi trường mà không sửa code. |
| `print()` cả câu hỏi, câu trả lời và key | 33–38 | Log khó truy vấn và lộ dữ liệu nhạy cảm. |
| Không có `/health` hay `/ready` | 25–39 | Platform không phân biệt process sống với sẵn sàng nhận tải. |
| Bind `localhost`, port `8000` cố định | 51–52 | Không nhận kết nối qua cổng mà container/platform cấp. |
| `reload=True` cố định | 53 | Tốn tài nguyên và có thể restart ngoài ý muốn khi chạy production. |
| Không có vòng đời shutdown/cleanup | 47–54 | Không đóng tài nguyên hoặc chủ động ngừng nhận request khi tắt. |

### Exercise 1.2 — Chạy bản develop

Chạy mẫu bằng Python 3.11 trong container tạm. `POST /ask?question=Hello` trả
**HTTP 200** và một câu trả lời từ mock LLM. Endpoint mẫu nhận `question` ở
query parameter (dòng 31), nên lệnh gửi JSON body trong `CODE_LAB.md` không đúng
với chữ ký hàm của chính bản develop. Container chỉ bind `localhost` bên trong;
kiểm tra HTTP được thực hiện từ trong container. Log của lần gọi in cả fake key,
đúng anti-pattern cần quan sát. Hai container thử nghiệm đã được dừng.

### Exercise 1.3 — So sánh bản production mẫu

Bản production mẫu chạy với `PORT=8001`, `DEBUG=false`,
`ENVIRONMENT=development`: `GET /health` **200**, `GET /ready` **200**,
`POST /ask` với JSON `{"question":"Hello"}` **200**.

| Feature | Develop | Production mẫu | Tại sao quan trọng? |
|---|---|---|---|
| Config và secrets | Literal trong code, dòng 17–22 | `Settings` đọc env trong `production/config.py` | Thay config và secret mà không sửa image/code. |
| Port và bind | `localhost:8000`, dòng 51–52 | `settings.host`/`settings.port`, dòng 194–198 | Container/cloud cần bind `0.0.0.0` và port được cấp. |
| Health/readiness | Không có | `/health` dòng 135; `/ready` dòng 152 | Liveness để restart, readiness để ngừng route traffic. |
| Logging | `print()` cả key, dòng 33–38 | Log có event/field, dòng 27–31 và 110–122 | Dễ tra cứu, không đưa key vào log. |
| Shutdown | Không có cleanup | `lifespan` đặt readiness false và cleanup, dòng 39–67 | Cho platform thời gian ngừng route và hoàn tất request. |
| Dev reload | Luôn bật | Chỉ bật khi `DEBUG=true`, dòng 198 | Không chạy reloader trong production. |

Lưu ý: bản production *mẫu* chỉ `sleep(0.1)` ở shutdown; riêng thao tác đó không
chứng minh mọi request kéo dài đều hoàn tất. Phần 6 có bài kiểm tra SIGTERM riêng.

Hardcode key trong repo public khiến bất kỳ ai đọc repo hoặc lịch sử Git có thể
dùng key, nên cần đặt key ở biến môi trường và xoay vòng nếu lộ. Stateless cho
phép nhiều instance dùng chung state ngoài process. Dev/prod parity nghĩa là
giữ runtime, dependency và cách chạy gần nhau để giảm lỗi chỉ xuất hiện khi deploy.

## Part 2 — Docker

### Exercise 2.1 — Dockerfile cơ bản

1. Base image là `python:3.11` (bản Python đầy đủ), ở dòng `FROM` của
   `02-docker/develop/Dockerfile`.
2. Working directory trong container là `/app` (`WORKDIR /app`).
3. `COPY requirements.txt` trước source để Docker có thể dùng lại layer cài
   dependencies khi chỉ sửa code. `pip --no-cache-dir` chỉ tắt cache của pip,
   không tắt Docker layer cache.
4. `CMD` cho lệnh/đối số mặc định khi chạy container và có thể bị thay bằng
   đối số sau tên image. `ENTRYPOINT` định nghĩa chương trình chính; đối số
   từ `CMD` hoặc `docker run` thường được truyền vào chương trình đó. Mẫu này
   dùng `CMD ["python", "app.py"]`.

### Exercise 2.3 — Multi-stage

`02-docker/production/Dockerfile` dùng stage `builder` cài gcc, libpq-dev và
Python packages vào `/root/.local`. Stage `runtime` bắt đầu lại từ
`python:3.11-slim`, chỉ copy packages và mã chạy, tạo user không phải root.
Compiler, apt cache và các file của builder không nằm trong image cuối. Bản
develop cũng dùng base Python đầy đủ, nên chênh lệch kích thước không chỉ do
multi-stage; phép so ở đây đồng thời thay base image.

### Exercise 2.2–2.3 — Kết quả build và chạy

Build hai Dockerfile từ gốc repo, đo bằng `docker image inspect ... --format
'{{.Size}}'` trên Docker Desktop (Python 3.11):

| Image | Dung lượng thực tế |
|---|---:|
| `k5-day14-part2-develop` | 1.667.776.517 byte = **1667,8 MB** |
| `k5-day14-part2-production` | 239.815.426 byte = **239,8 MB** |

Image production nhỏ hơn **85,6%**, tính `(develop - production) / develop`.
Container develop: `GET /health` **200**, `POST /ask?question=What%20is%20Docker%3F`
**200**. Code develop khai báo `question: str` là query parameter; lệnh gửi JSON
body trong Exercise 2.2 không khớp với mẫu này. Container thử đã được dừng.

### Exercise 2.4 — Kiến trúc Compose mẫu

```text
Client -> Nginx :80 -> agent :8000
                         |-> Redis :6379 (session/cache)
                         `-> Qdrant :6333 (vector store)
```

Compose khai báo `agent`, `redis`, `qdrant`, `nginx` trên network `internal`.
`agent` chờ Redis và Qdrant healthy; Nginx proxy vào tên service `agent` qua
Docker DNS. Redis và Qdrant có named volume; chỉ Nginx publish port ra host.
Code agent mẫu hiện chưa gọi Redis/Qdrant; Compose chuẩn bị kết nối bằng biến
môi trường để minh hoạ kiến trúc.

Đã chạy `docker compose -p k5-day14-part2 ... up -d --build`: cả bốn service
đều running, agent/Redis/Qdrant healthy. Gọi qua Nginx `GET /health` **200**
và `POST /ask` với JSON **200**. Đã `down -v` và xóa file env trống tạm.

## Part 3 — Cloud Deployment

### Exercise 3.1 — Railway

Agent Part 6 được deploy từ **fork `Basrot`**, nhánh `codex/part6-render`, tại
https://day14-agent-production-3dd6af85.up.railway.app . Project Railway có
service agent Docker và Redis private với volume. `AGENT_API_KEY` nằm trong
Railway Variables, không ghi vào Git. Kiểm tra lại ngày 2026-11-26:

| Lệnh kiểm tra | HTTP |
|---|---:|
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` không key | 401 |
| `POST /ask` có key hợp lệ | 200 |

Chi tiết build, biến môi trường và cách tái kiểm tra ở `DEPLOYMENT.md`;
report HTTP không chứa key ở `06-lab-complete/verification/railway-public.json`.

### Exercise 3.2 — So sánh với Render

`railway.toml` trong Part 6 mô tả builder Dockerfile, healthcheck `/health` và
restart của **một service**. Trên Railway, Redis được thêm bằng template riêng,
`REDIS_URL` tham chiếu biến của Redis trong project và các service settings
hiện hành chứa root directory `/06-lab-complete`, nhánh Git và resource limit.
`render.yaml` là Blueprint mô tả **cả** web service lẫn Key Value/Redis,
kèm reference `fromService`, biến sinh tự động và cấu hình từng service trong
cùng một file. Cả hai chạy cùng Dockerfile và kiểm tra `/health`; khác nhau ở
phạm vi file cấu hình và cách nối Redis. Render planning bị chặn bởi trạng thái
`billing_suspended` của workspace, nên Railway là nền tảng deploy chính.

### Exercise 3.3 — Pipeline Cloud Run (đọc cấu hình, không deploy)

`03-cloud-deployment/production-cloud-run/cloudbuild.yaml` chạy pytest trước;
nếu pass, build Docker image gắn `$COMMIT_SHA` và `latest`, rồi push lên
Container Registry. Bước cuối deploy image theo commit lên Cloud Run ở
`asia-southeast1`, lấy secret từ Secret Manager, đặt giới hạn CPU/RAM và số
instance. `service.yaml` mô tả cùng service dưới dạng cấu hình: ingress public,
concurrency 80, min/max scale 1/10, `/health` liveness và `/ready` startup.

## Part 4 — API Security

### Exercise 4.1 — API key

`04-api-gateway/develop/app.py` đọc `AGENT_API_KEY` khi start và kiểm tra
header `X-API-Key` trong dependency `verify_api_key` trước `/ask`.
Chạy mẫu local với key demo từ đề; kết quả HTTP:

```text
POST /ask, không X-API-Key       -> 401
POST /ask, X-API-Key sai         -> 403
POST /ask, X-API-Key hợp lệ      -> 200
```

Bản mẫu trả 403 khi key **sai**, khác 401 khi **thiếu**. Rotate key bằng cách đổi
biến môi trường của service và restart; để chuyển đổi không gián đoạn cần cho
phép hai key trong một thời gian ngắn rồi thu hồi key cũ. Không log key thật.

### Exercise 4.2–4.3 — JWT và rate limit

Bản production mẫu dùng `POST /auth/token`, `student`/`demo123` như ghi chú K5
trong `README.md`. Endpoint xác thực user, ký JWT HS256 có `sub`, `role`, `iat`
và `exp` 60 phút; `/ask` xác minh chữ ký và hạn dùng trong `verify_token`.
Chạy local với `JWT_SECRET` ngẫu nhiên cho lần thử; token không được ghi vào bài:

```text
POST /ask, không Bearer token    -> 401
POST /auth/token, đúng tài khoản -> 200 (token đã che)
POST /ask, Bearer token hợp lệ   -> 200
20 POST /ask tiếp theo           -> 9 lần 200, 11 lần 429
```

Request hợp lệ đầu tiên đã dùng 1/10 suất của `student`, nên trong vòng lặp
20 lần chỉ 9 lần tiếp theo nhận 200. `rate_limiter.py` giữ deque timestamp
trong cửa sổ trượt 60 giây: user 10 request/phút, admin 100 request/phút.
Admin dùng limiter riêng, không hoàn toàn bỏ giới hạn. State này ở RAM nên
chỉ phù hợp demo một process; Part 6 chuyển sang Redis để nhiều worker dùng chung.

### Exercise 4.4 — Cost guard $10/tháng trên Redis

Mẫu `production/cost_guard.py` sẵn có là **budget theo ngày trong RAM** ($1/user,
$10 toàn hệ thống), khác yêu cầu riêng của Exercise 4.4. Mình bổ sung
`production/monthly_budget.py`: `check_budget(user_id, estimated_cost)`
chuyển USD sang số nguyên nano-USD, dùng Redis Lua để kiểm tra và cộng chi phí
ước tính **atomic** theo từng user/tháng UTC. Key hết hạn đầu tháng sau;
vượt $10 trả `False`, lỗi Redis không được coi là cho phép chi tiêu.
Kiểm tra với Redis thật: **4/4 test pass**, gồm $6+$4 rồi chặn $0,01, tách
user, 20 yêu cầu đồng thời chỉ 16 lần $0,60 được nhận, và từ chối cost âm/NaN.

Rate limit chặn tần suất, cost guard chặn tổng chi tiêu; request ít nhưng
prompt dài vẫn có thể tốn nhiều tiền, còn request rẻ nhưng quá dày vẫn gây tải.
Trong production thật cần đối soát chi phí thực sau LLM với số đã đặt trước,
và bảo vệ cả global budget; ví dụ này chỉ thực hiện phần ước tính của bài tập.

## Part 5 — Scaling & Reliability

### Exercise 5.1–5.2 — Health, readiness, shutdown

Chạy `05-scaling-reliability/develop/app.py` bằng Python 3.11 trong container
tạm. `GET /health` **200** (status `ok`, memory 9,1% ở lần đo), `GET /ready`
**200** (`ready=true`). Health phản ánh process còn sống để platform quyết định
restart; readiness cho load balancer biết instance có nhận traffic mới được
không. Endpoint `/ready` của mẫu trả 503 khi `_is_ready=false`; Part 6 còn kiểm
thêm Redis thật.

Gửi hai `POST /ask?question=long...` rồi `docker stop -t 12` sau 0,5 giây:
**cả hai request trả 200** (3,06 và 6,06 giây), Docker stop exit 0. Hai request
được xử lý nối tiếp vì mock `ask()` dùng `time.sleep` trong async endpoint;
đây là số đo của lần thử, không suy ra khả năng chịu tải production.

### Exercise 5.3–5.5 — Redis session và load balancing

Chạy stack `k5-day14-scaling` với **3 agent + Redis + Nginx** tại port 8080.
`POST /chat` tạo `session_id`, mỗi lượt đọc/ghi `session:<id>` trong Redis với
TTL một giờ; response ghi `served_by`. `test_stateless.py` nguyên bản gửi 5
request: chúng được phục vụ bởi **3 instance khác nhau**, lịch sử vẫn đủ
**10 message** (5 user + 5 assistant). Script nguyên bản không dừng instance,
nên mình thực hiện phép thử failover riêng.

Sau khi dừng một agent, request đầu **timeout sau 10 giây**: Nginx đã cache
địa chỉ upstream cũ. Mình sửa `production/nginx.conf` bằng shared `zone` và
`server agent:8000 resolve`, kiểm tra `nginx -t` pass rồi reload. Trong trạng
thái chỉ còn 2 agent, **10/10 POST /chat trả 200**, `served_by` thuộc cả hai
instance còn lại, history đủ **20 message** (10 lượt). Kết quả này xác nhận
failover sau sửa cấu hình. Stack và file env trống tạm đã được dọn.

State trong RAM riêng của từng process khiến lượt 2 có thể đi tới instance
không thấy lượt 1. Redis làm nơi lưu chung để bất kỳ instance nào cũng đọc
session. Mẫu `production/app.py` còn có fallback về in-memory nếu Redis chết
ngay lúc start; đó là giới hạn của demo, không nên dùng fallback này cho
production thật. Part 6 đã loại bỏ fallback.

## Part 6 — Production-ready agent

Code ở `06-lab-complete/`. Kiểm tra ngày 2026-11-26 bằng script chấm nguyên bản
trong Linux container, với Docker Desktop và Redis thật.

```text
📋 Checklist Deliverable
✅ Dockerfile (multi-stage, < 500 MB)
✅ docker-compose.yml (agent + redis)
✅ .dockerignore
✅ Health check endpoint (GET /health)
✅ Readiness endpoint (GET /ready)
✅ API Key authentication
✅ Rate limiting
✅ Cost guard
✅ Config từ environment variables
✅ Structured logging
✅ Graceful shutdown
✅ Public URL ready (Railway / Render config)
Result: 12/12 tiêu chí đạt · 43/43 checks passed
PASS 12/12 — PRODUCTION READY!
```

Output đầy đủ: `06-lab-complete/verification/part6-readiness.txt`.
Image 274 MB; Docker stop 0,8 giây, exit code 0. Integration tests: 14/14.
`Public URL ready` trong script là kiểm tra cấu hình deploy; URL cloud đã được
kiểm tra riêng theo `DEPLOYMENT.md`: 200/200/401/200, report `railway-public.json`.

Render planning thất bại với `billing_suspended`. Học viên đã chuyển sang Railway:
agent và Redis đều chạy, URL public là
https://day14-agent-production-3dd6af85.up.railway.app . Kiểm tra thực tế ngày
2026-11-26 lúc 17:23 GMT+7: `/health` 200, `/ready` 200, `/ask` không key 401,
có key 200. Nguồn deploy chỉ ở fork `Basrot/...`, nhánh `codex/part6-render`.
Ba ảnh CP6 đã lưu tại `screenshots/dashboard.png`, `screenshots/running.png`
và `screenshots/test.png`; liên kết và kết quả kiểm tra ở `DEPLOYMENT.md`.

Các điểm cần giải thích:

- `/health` chỉ phản ánh process sống; `/ready` kiểm tra Redis để quyết định nhận tải.
- API key so sánh bằng `compare_digest`; thiếu cấu hình key thì từ chối truy cập.
- Sliding window 60 giây chạy bằng Redis Lua để thao tác kiểm tra/cập nhật atomic
  giữa các worker. State dùng fingerprint key, không lưu API key nguyên văn.
- Chi phí cộng bằng số nguyên nano-USD trong Redis, tự hết hạn lúc nửa đêm UTC.
- Uvicorn nhận SIGTERM, đợi request xong; lifespan đóng client Redis sau đó.
- Code không lưu session, rate limit hoặc budget trong RAM của worker.

## AI log

| Ngày | Yêu cầu gửi AI | Hỗ trợ nhận được | Tự sửa và tự kiểm tra |
|---|---|---|---|
| 2026-11-26 | Đọc và tóm tắt Lab 14 | Giải thích yêu cầu, checkpoints, rubric và bài nộp | Cần học viên đọc lại các tài liệu gốc và xác nhận hiểu |
| 2026-11-26 | Hoàn thiện Part 6 rồi deploy Render theo đề | Codex viết config, auth, Redis rate limit/cost guard, endpoints, logging, Docker, Compose, Blueprint và integration tests; review độc lập phát hiện lỗi PORT trong Compose và đã sửa | Codex chạy 14 test với Redis thật, script chấm nguyên bản 42/42 trên Linux; kiểm tra lại cổng tùy chỉnh. Học viên cần tự chạy lại và giải thích code; chưa ghi nhận thao tác tự kiểm tra của học viên |
| 2026-11-26 | Chuyển qua Railway, chỉ push fork cá nhân | Codex bổ sung railway.toml, tạo project agent + Redis private có volume, đặt biến môi trường và deploy nhánh trong fork; không thay đổi repo chương trình | Codex chạy lại checker đạt 43/43, kiểm tra public 200/200/401/200 và lưu report không chứa key; học viên cần tự kiểm tra lại và giải thích |
| 2026-11-26 | Hoàn thiện Part 1–5 theo thứ tự đề | Codex đọc code mẫu, chạy Part 1, build/đo Part 2, kiểm lại Railway/Cloud Run Part 3, chạy auth/JWT/rate limit Part 4, viết guard tháng Redis và thử scaling Part 5 | Codex đo image 1667,8/239,8 MB, HTTP và session thực tế, chạy 4 test Redis, phát hiện rồi sửa timeout Nginx; học viên cần đọc lại, tự chạy và giải thích các số liệu |
| 2026-11-26 | Tiếp tục Part 7 theo thứ tự rồi làm Part 8 | Codex chạy load test ở 4 mức concurrency và 3 mức slow rate, eval v1/v2 và sửa 2 mục KB, thêm quality gate CI; báo cáo số thật ở `BENCHMARK_REPORT.md` | Codex xác nhận 11 JSON hợp lệ, eval v2 sau sửa 23/23 và gate v1 regression thất bại; lúc đầu hệ thống duyệt Docker báo hết credits, sau đó chạy được khi thử lại. Học viên cần tự kiểm tra và giải thích |
| 2026-11-26 | Tiếp tục đo Part 8 sau khi xác minh mức sử dụng tài khoản | Codex dựng lại stack, chạy promtool, đo Locust 1/3 replica, đối chiếu log/trace và chạy fault injection A–E | Docker image đã chạy healthy; alert A–D firing sau 87,8/148,1/143,6/40,4 giây; eval production v1 đúng 1/23, gate fail và không có alert chất lượng. Locust đã dừng, agent trả về v2; 7 ảnh minh chứng đã được thêm. Workflow quality gate chưa chạy trên GitHub |

Không thay đổi `check_production_ready.py` hoặc golden dataset; số đo trong phần
này lấy từ file output thực tế, không lấy từ số ví dụ trong tài liệu lab.
