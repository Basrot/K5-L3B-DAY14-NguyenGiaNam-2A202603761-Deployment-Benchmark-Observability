# Part 6 — Render deployment

## Trạng thái

Part 6 đã được kiểm tra local ngày 2026-11-26:

- Script chấm nguyên bản trên Linux: **PASS 12/12**, **42/42 checks passed**.
- Integration test với Redis thật: **14 tests passed**.
- Stack Compose với `PORT=18014`: `/health` 200, `/ready` 200, `/ask` không key 401,
  `/ask` có key 200; report `06-lab-complete/verification/part6-compose.json`.
- Image: **274 MB**, dưới giới hạn 500 MB.
- SIGTERM khi có request: request trả 200, process thoát với exit code 0.
- Docker stop: exit code 0, **0.7 giây** trong lần chạy ghi nhận.

Bằng chứng: `06-lab-complete/verification/part6-readiness.txt` và
`06-lab-complete/verification/part6-integration.txt`.
**Cloud đang bị chặn:** Render trả `billing_suspended` khi lập kế hoạch Blueprint
ngày 2026-11-26 cho cả Web Service và Key Value. Chưa có URL public, service mới
chưa được tạo/chạy và chưa có kết quả HTTP cloud. Cần chủ tài khoản xử lý trạng
thái Billing của workspace trước khi tiếp tục.

- Workspace đã được học viên xác nhận: `My Workspace`.
- Nhánh đã push: `codex/part6-render`.
- Commit triển khai: `9049617`.
- Blueprint: `exs-dc3u5l6c6qcc73buhek0` (`Day14 Production Agent`).
- Planning outcome: `failed`; sync: `null`; không approve một plan thất bại.
- Auto-sync đang tắt; sau khi Billing được xử lý, lập plan lại và duyệt thay đổi
  tạo 2 dịch vụ Free trước khi apply.

Nguồn đã push: [nhánh triển khai](https://github.com/Basrot/K5-L3B-DAY14-NguyenGiaNam-2A202603761-Deployment-Benchmark-Observability/tree/codex/part6-render).
Xử lý tài khoản: [Render Billing](https://dashboard.render.com/billing).

## Kiến trúc và cấu hình

Client → Render Docker Web Service → mock LLM; Redis lưu sliding window và chi phí.
Blueprint: `06-lab-complete/render.yaml`, root directory `06-lab-complete`.
Web Service và Key Value dùng Free plan, Singapore, kết nối qua private network.

| Biến | Nguồn / ý nghĩa |
|---|---|
| `AGENT_API_KEY` | Render sinh ngẫu nhiên; không lưu giá trị trong repo |
| `REDIS_URL` | Blueprint lấy connectionString của Key Value |
| `RATE_LIMIT_PER_MINUTE` | 10 request / 60 giây / API key |
| `DAILY_BUDGET_USD` | 1.0 USD, reset theo ngày UTC |
| `ENVIRONMENT` | production |
| `PORT` | Render cấp; Docker mặc định 8000 |

Health check: `/health`. `/ready` kiểm tra Redis riêng và trả 503 khi mất kết nối.
Redis không truy cập được thì `/ask` trả 503; không chuyển sang state trong RAM.

## Kiểm tra public sau khi deploy (Bash / WSL)

Đặt `BASE` bằng URL thực tế, nhập key từ trang Environment của Render vào terminal
cá nhân. Không ghi key vào file báo cáo hoặc ảnh chụp.

```bash
read -rsp 'AGENT_API_KEY: ' AGENT_API_KEY; echo
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
unset AGENT_API_KEY
```

Kỳ vọng lần lượt 200, 200, 401, 200. Đã xác minh chuỗi này trên Compose local;
chưa xác minh cloud do lỗi Billing nêu trên. Cần lưu 3 ảnh deploy theo
`SUBMISSION.md` sau khi service live.

## Chạy local và kiểm tra lại

Trong `06-lab-complete/`, copy `.env.example` thành `.env` và đặt API key ngẫu nhiên.
Chạy `docker compose -p k5-day14-final up -d --build --wait`.
Sau đó kiểm tra `http://localhost:8000/health` và `/ready`.

Linux/WSL: cài `requirements.txt`, chạy `python check_production_ready.py`.
Windows có Docker Desktop và PowerShell 7: chạy
`pwsh -NoProfile -File 06-lab-complete/tests/check-linux.ps1` từ gốc repo.
Harness dùng Linux và Redis tạm trên cổng 16380 (đổi bằng `-RedisPort`),
chạy script chấm nguyên bản, không sửa hoặc bỏ qua tiêu chí nào.

## Giới hạn demo

- Token và cost của mock được ước lượng từ độ dài văn bản, có `usage.estimated=true`.
- Budget kiểm tra trước khi gọi LLM và cộng sau khi trả lời; các request đồng thời
  đã được chấp nhận có thể làm tổng chi phí vượt ngưỡng trước khi lần gọi sau bị chặn.
- Key Value Free không bền vững khi datastore restart; state vẫn được chia sẻ giữa
  worker và tồn tại khi chỉ restart agent. Compose local bật AOF và named volume.
- Free Web Service có thể ngủ khi không có traffic. Benchmark Part 7 chạy local
  trên stack riêng theo đề.
