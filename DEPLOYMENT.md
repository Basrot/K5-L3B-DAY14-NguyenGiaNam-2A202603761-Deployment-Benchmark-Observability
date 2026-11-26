# Part 6 — Railway deployment

## URL và kết quả thực tế

**URL public:** https://day14-agent-production-3dd6af85.up.railway.app

- [Health](https://day14-agent-production-3dd6af85.up.railway.app/health)
- [Readiness](https://day14-agent-production-3dd6af85.up.railway.app/ready)
- [API docs](https://day14-agent-production-3dd6af85.up.railway.app/docs)
- [Railway project](https://railway.com/project/4a362d25-2fc8-43ea-9e75-2a7b526494f7)

Kiểm tra public ngày **2026-11-26 lúc 14:54 GMT+7** bằng HTTP thật:

| Yêu cầu | Kết quả |
|---|---:|
| GET /health | 200 |
| GET /ready | 200 |
| POST /ask không có API key | 401 |
| POST /ask có API key hợp lệ | 200 |

Report: `06-lab-complete/verification/railway-public.json`.
Script kiểm tra: `06-lab-complete/tests/check_public.py`.
API yêu cầu JSON, ví dụ `{"question":"Hello"}`, và header `X-API-Key`.

## Nguồn code và trạng thái deploy

Chỉ deploy và push vào **fork của học viên**:
[Basrot / repo bài làm](https://github.com/Basrot/K5-L3B-DAY14-NguyenGiaNam-2A202603761-Deployment-Benchmark-Observability/tree/codex/part6-render).

- Nhánh: `codex/part6-render` (giữ tên nhánh từ giai đoạn chuẩn bị Render).
- Commit code/cấu hình deploy: `0c73b13`.
- Không push vào repo gốc `VinUni-AI20k/...`; không thay đổi nhánh `main`.
- Workspace Railway: `Nam Nguyễn 's Projects`.
- Project: `Lab14 Production Agent` (`4a362d25-2fc8-43ea-9e75-2a7b526494f7`).
- Environment: `production` (`ac71a226-29db-42be-90b0-0fb0b2676b42`).
- Agent: `day14-agent` (`45789e8f-5d14-42f7-8a47-b0f6fe89da74`).
- Agent deployment: `eaf7bc66-30a6-4eeb-bdcf-08ac3ffdef5c`, **SUCCESS**.
- Redis: `3a8b2f7b-f7f2-4a0b-8fc4-6508e610637e`, template chính thức `redis:8.2`,
  volume `/data` **500 MB**, không bật TCP proxy public.
- Cả agent và Redis chạy tại region `iad`, 1 instance mỗi service.
- Dùng credit/gói sẵn có; không nâng lên gói trả phí hoặc thêm phương thức thanh toán.

## Cấu hình Railway

Client HTTPS → Railway Docker agent → mock LLM.
Agent → Redis qua private network để chia sẻ rate limit và budget giữa các worker.

| Thiết lập | Giá trị |
|---|---|
| Repository | Fork `Basrot/...`, nhánh `codex/part6-render` |
| Root directory | `/06-lab-complete` |
| Builder / Dockerfile | `DOCKERFILE` / `Dockerfile` |
| Start command | Dùng CMD của Dockerfile, `exec uvicorn`, 2 workers |
| Health check | `/health`, timeout 120 giây |
| Draining | 9 giây |
| Restart | ON_FAILURE, tối đa 3 lần |
| Resource limit của agent | 1 vCPU, 500 MB RAM |
| Sleep application | Bật |

Railway hiện chuyển từ file legacy `railway.toml` sang service settings/IaC cho
service mới. Vì vậy root, Dockerfile, health check và restart đã được đặt trực tiếp
trên service; `railway.toml` vẫn được nộp theo hợp đồng lab.
Tham khảo: [Railway IaC](https://docs.railway.com/infrastructure-as-code).

Watch paths chỉ bao gồm code app, utils, Dockerfile, requirements, dockerignore và
railway.toml của Part 6 để báo cáo/ảnh không gây build lại ứng dụng.

| Biến | Nguồn / ý nghĩa |
|---|---|
| `AGENT_API_KEY` | Khóa ngẫu nhiên riêng, đặt qua Railway Variables |
| `REDIS_URL` | `${{Redis.REDIS_URL}}`, dùng kết nối private có mật khẩu |
| `RATE_LIMIT_PER_MINUTE` | 10 request / 60 giây / API key |
| `DAILY_BUDGET_USD` | 1.0 USD, reset theo ngày UTC |
| `ENVIRONMENT` | production |
| `PORT` | 8000, domain target port 8000 |

Bản local của API key nằm ở `06-lab-complete/.env.railway`, đã gitignore.
Không chép giá trị vào báo cáo, ảnh chụp hoặc commit. Có thể xem/quản lý key trong
Variables của service trên Railway.

## Tái kiểm tra public

Từ `06-lab-complete/`, dùng file key local hoặc biến môi trường:

```bash
python tests/check_public.py --url https://day14-agent-production-3dd6af85.up.railway.app --key-file .env.railway --out verification/railway-public.json
```

Script chỉ in mã HTTP, không in key. Trên máy khác, đặt `AGENT_API_KEY` trong
môi trường cá nhân rồi bỏ tham số `--key-file`. Có thể cold start khi service ngủ.

## Bằng chứng local

- Script chấm nguyên bản trên Linux: **PASS 12/12**, **43/43 checks passed**.
- Integration tests với Redis thật: **14/14**.
- Compose với `PORT=18014`: **200, 200, 401, 200**.
- Image local: **274 MB**, dưới giới hạn 500 MB.
- SIGTERM khi đang có request: request trả 200, process thoát exit code 0.
- Docker stop: exit code 0, **0.7 giây** trong lần kiểm tra đã lưu.

File output ở `06-lab-complete/verification/`: `part6-readiness.txt`,
`part6-integration.txt`, `part6-compose.json`.

Linux/WSL: cài `requirements.txt` rồi chạy `python check_production_ready.py`.
Windows có Docker Desktop và PowerShell 7: từ gốc repo chạy:

```powershell
pwsh -NoProfile -File 06-lab-complete/tests/check-linux.ps1
```

Harness dùng Linux và Redis tạm trên cổng 16380 (đổi bằng `-RedisPort`),
chạy script chấm nguyên bản, không bỏ qua tiêu chí.

## Render và Railway (Part 3)

`render.yaml` mô tả cả Web Service và Redis, nối bằng `fromService`, sinh API key
bằng `generateValue`. `railway.toml` legacy mô tả build/deploy của một service;
Redis và reference variables được cấu hình ở cấp project/service trên Railway.
Cả hai dùng cùng Dockerfile, PORT động và health check /health.

Render đã được thử nhưng trả `billing_suspended`: workspace vượt bandwidth
5.83/5 GB và không có thẻ. Blueprint `exs-dc3u5l6c6qcc73buhek0` planning thất bại,
chưa tạo service chạy. Học viên sau đó chọn Railway; không tiếp tục deploy Render.
Report lịch sử: `06-lab-complete/verification/render-planning.json`.

## Giới hạn và phần bài nộp còn lại

- Token/cost của mock là ước lượng độ dài văn bản, có `usage.estimated=true`.
- Budget kiểm tra trước và cộng sau lời gọi LLM; request đồng thời đã được chấp nhận
  có thể làm tổng vượt ngưỡng trước khi lần gọi sau bị chặn.
- Redis có volume, nhưng chưa cấu hình HA/backup; đây là deployment lab.
- Để nộp đủ CP6, cần 3 ảnh thật `screenshots/dashboard.png`, `running.png`,
  `test.png`. Chưa đưa ảnh thay thế hoặc ảnh giả vào repo.
- Part 1–5 và Part 7 vẫn cần thực hành/báo cáo riêng theo CHECKPOINTS.
