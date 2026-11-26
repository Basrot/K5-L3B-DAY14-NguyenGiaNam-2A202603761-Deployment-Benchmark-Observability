# Day 14 — Mission Answers

Part 1–5 chưa có kết quả thực hành trong phiên triển khai Part 6 này; cần hoàn
thành riêng theo `CHECKPOINTS.md`. Phần dưới ghi nhận kết quả Part 6 thực tế.

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
Result: 12/12 tiêu chí đạt · 42/42 checks passed
PASS 12/12 — PRODUCTION READY!
```

Output đầy đủ: `06-lab-complete/verification/part6-readiness.txt`.
Image 274 MB; Docker stop 0.7 giây, exit code 0. Integration tests: 14/14.
`Public URL ready` trong script là kiểm tra cấu hình deploy; URL cloud cần được
kiểm tra riêng theo `DEPLOYMENT.md` sau khi dịch vụ live.

Deploy Render đã được thử qua kết nối Render: tạo Blueprint thành công nhưng
planning thất bại với `billing_suspended`. Chưa tính hoàn thành nhóm Deployment
của Part 6 và phần URL public của Part 3.

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

Không thay đổi `check_production_ready.py` hoặc golden dataset; số đo trong phần
này lấy từ file output thực tế, không lấy từ số ví dụ trong tài liệu lab.
