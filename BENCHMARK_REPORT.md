# Benchmark & Observability Report — Day 14

> Số liệu dưới đây lấy từ JSON/CSV của chính lần chạy Lab 14; các mục chưa đo
> được sẽ ghi rõ trạng thái, không dùng số ví dụ của tài liệu.

**Họ tên:** Nguyễn Gia Nam

**Ngày chạy:** 2026-11-26

**Môi trường:** Windows, Python 3.11.9; benchmark develop chạy local. Docker
Desktop cấp 8 CPU và 8.015 GB RAM cho phần stack. Mock LLM, không gọi API trả phí.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Giới hạn trải nghiệm của ít nhất 95% request theo `load_test.py`. |
| Error rate `/ask` | ≤ 2% | Cho phép tối đa 2 lỗi trên 100 request, cùng ngưỡng script lab. |
| Accuracy trên golden dataset | ≥ 80% | Gate mặc định của lab; sau sửa KB chạy gate chặt hơn ở 100%. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4,11 | 206,8 | 246,8 | 1710,4 | 1,00% | PASS |
| 10 | 37,61 | 200,5 | 242,4 | 1666,4 | 0,67% | PASS |
| 50 | 91,95 | 217,8 | 739,3 | 1733,2 | 0,33% | FAIL (p95) |
| 100 | 41,09 | 1096,8 | 5232,8 | 5495,5 | 1,00% | FAIL (p95) |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

Mỗi mức có 300 request. RPS tăng từ 1 lên 50 concurrent rồi giảm ở 100;
p95 vượt ngưỡng từ 50. Khả năng xử lý của máy/server và chi phí điều phối
request là hữu hạn, nên tăng concurrency không tạo throughput tuyến tính.
Ở 100, tail latency và tranh chấp tài nguyên làm cả RPS giảm. Các số gốc:
`reports/load_v2_c1.json`, `load_v2_c10.json`, `load_v2_c50.json`,
`load_v2_c100.json`.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 199,5 | 234,6 | 247,9 |
| 0.03 (mặc định) | 261,1 | 254,5 | 1716,9 |
| 0.1 | 328,5 | 1689,4 | 1730,7 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

Cùng 300 request và concurrency 20. Ở tỉ lệ chậm 3%, p99 tăng mạnh trong
khi p95 vẫn dưới 500 ms; ở 10%, p95 cũng nhảy lên 1689,4 ms. Average chỉ tăng
từ 199,5 lên 261,1 rồi 328,5 ms, nên che trải nghiệm của nhóm bị chậm.
SLO dùng percentile để nêu rõ tỉ lệ người dùng chịu latency cao. File gốc:
`reports/load_v2_slow_0.json`, `load_v2_slow_0.03.json`, `load_v2_slow_0.1.json`.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 1/23 (4,35%) | 21/23 (91,30%) | 23/23 (100%) |
| Avg tokens / câu | 56,7 | 109,1 | 113,1 |
| Tổng cost (USD) | 0,000399 | 0,000762 | 0,000786 |
| Cost / câu đúng (USD) | 0,00039855 | 0,00003627 | 0,00003417 |
| Quality gate | FAIL (80%) | PASS (80%, không regression so với v1) | PASS (100%, không regression so với v2 ban đầu) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm mục JWT so với API key, nêu token có chữ ký và hạn dùng. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm mục Kubernetes HPA theo ba loại chỉ số đó. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

Retrieval làm v2 dùng thêm token và tổng cost gần gấp đôi v1, nhưng accuracy
tăng từ 1 lên 21 câu đúng; cost trên mỗi câu đúng giảm hơn 10 lần. Sau khi
thêm đúng hai mục KB, accuracy 100% và cost trên câu đúng còn 0,00003417 USD.
Eval dùng 23 câu cố định, không đủ mẫu để suy ra p95 latency; latency ở mục 2
lấy từ load test 300 request.

`reports/eval_v1.json`, `eval_v2.json`, `eval_v2_fixed.json` là số gốc.
Chạy v1 với `--baseline reports/eval_v2.json` tạo
`reports/eval_v1_regression.json`: gate **FAIL**, exit code 1, 20 câu bị
regression. Workflow `.github/workflows/day14-quality-gate.yml` khởi động v2,
đợi `/health`, rồi chạy eval với `--min-accuracy 1.0` và baseline v2 ban đầu.
Exit code 1 làm job thất bại; branch protection có thể dùng job này để chặn
merge/deploy khi có regression. Không dùng `continue-on-error`.

---

## 4. Observability stack (production)

Docker image ban đầu không khởi động vì runtime không tìm thấy `uvicorn` trong
user site. Sau khi thêm `PYTHONUSERBASE=/home/agent/.local`, image build lại và
agent healthy. `/ask` qua Nginx trả 200 kèm `X-Trace-ID` và `X-Served-By`;
`/metrics` qua Nginx trả 404. Prometheus thấy 1 rồi 3 target agent ở trạng
thái `up`. `promtool test rules` báo `SUCCESS` cho alert rules.

### 4.1 Screenshot

- [ ] `screenshots/grafana-dashboard.png` — dashboard Grafana khi có tải, thấy Golden Signals.
- [ ] `screenshots/jaeger-slow-trace.png` — trace chậm, thấy thời gian từng span.
- [ ] `screenshots/jaeger-error-trace.png` — trace lỗi có event `exception`.
- [ ] `screenshots/prometheus-alert-firing.png` — trang Alerts có hai alert cùng `firing`.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 87,8 giây | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 148,1 giây | p95 latency (đo ~1,92 s khi pending) |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | 143,6 giây | Cost USD/giờ (đo ~8,55 USD/giờ khi pending) |
| D | `docker pause` 1 instance | `AgentInstanceDown` | 40,4 giây | Instances up; agent đã `unpause` sau khi đo |
| E | `AGENT_VERSION=v1` | Không có alert chất lượng; sau khi cửa sổ cost của C hết, không còn alert nào | Không áp dụng | Bảng version đổi sang v1; quality gate 1/23 |

Thời gian tính từ lúc đổi cấu hình hoặc pause tới lần poll API đầu tiên thấy
`firing` (poll mỗi 5 giây), nên sai số quan sát tối đa khoảng 5 giây. JSON
gốc ở `observability-results/experiment-a.json` đến `experiment-d.json`;
`alerts-d.json` lưu trạng thái Prometheus lúc D firing. Mỗi lần thử A–E đều
có tải Locust 30 users. C dùng mock model, không gọi API trả phí. Khi mới đổi
sang v1, alert cost của C còn firing do cửa sổ 5 phút; đến 09:44:32 UTC nó
biến mất và danh sách alert rỗng dù v1 vẫn phục vụ 30 users.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Eval trên endpoint production v1 đúng 1/23 câu (4,35%), fail quality gate và
20 câu regression so với baseline v2 (`reports/eval_production_v1.json`).
Prometheus thấy cả 3 target mang `version=v1` nhưng không có alert khi dữ
liệu C đã hết cửa sổ (`observability-results/experiment-e-cleared.json`).
Metric latency, error và uptime không đo câu trả lời đúng hay sai. Production
cần chạy golden dataset theo lịch và trước mỗi release, theo dõi accuracy và
regression theo phiên bản, rồi bổ sung phản hồi người dùng cho câu hỏi thực tế.

### 4.3 Debug bằng trace

Trace chậm nhất tìm được trong log của lần đo (đối chiếu Jaeger API v3):

- `trace_id`: `c9d2cf08b3cc46df43ff7bcb18a22f68`
- Tổng thời gian span `POST /ask`: 1727,4 ms
- Span chiếm nhiều thời gian nhất: `chat mock-llm-small` 1698,8 ms (98,3%);
  retrieval chỉ 24,3 ms.
- Dòng log tương ứng (lọc theo `trace_id`):

```json
{"event":"llm_call","trace_id":"c9d2cf08b3cc46df43ff7bcb18a22f68","model":"mock-llm-small","llm_ms":1698.7,"cost_usd":0.000047}
```

Trace lỗi `c5f209c8d71ad3bba6a2df2627eac6f2` có event `exception`
trong span `chat mock-llm-small` (74,4 ms, status error) và `agent.run`.
Log cùng `trace_id` ghi `llm_error`: `Upstream LLM error: 503 Service
Unavailable (mock)`.

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 60,25 | 200 | 280 | 1700 | 70/7211 (0,97%) |
| 3 | 59,75 | 190 | 230 | 1700 | 82/7151 (1,15%) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

Với cùng 100 users, ramp 10 users/giây và 2 phút, p95 `/ask` giảm từ 280 xuống
230 ms (17,9%) khi scale 1 → 3 agent; p99 vẫn 1700 ms, RPS gần như không đổi.
Mỗi user Locust nghỉ ngẫu nhiên 0,5–2 giây giữa các request, nên tốc độ phát
tải bị giới hạn bởi kịch bản; chưa đạt mức đủ lớn để chứng minh throughput
scale tuyến tính. Tail p99 đến từ mock LLM cố tình tạo request chậm. Lỗi 503
đến từ `MOCK_ERROR_RATE=0.01`, nên số lỗi chênh lệch giữa hai lượt là dao động
thực nghiệm. CSV gốc: `benchmark-results/scale_1_stats.csv` và
`scale_3_stats.csv` (cùng các file history/failures/exceptions).

---

## 6. Kết luận

- 3 điều rút ra từ dữ liệu đã đo:
  1. Ở concurrency 100, RPS giảm còn 41,09 và p95 tăng lên 5232,8 ms; thêm
     request đồng thời sau điểm bão hoà làm hiệu năng xấu đi.
  2. Khi tỉ lệ request chậm tăng từ 0 lên 3%, p99 tăng từ 247,9 lên 1716,9 ms
     dù p95 vẫn dưới 500 ms; percentile thể hiện tác động mà average che mất.
  3. Retrieval tăng tổng cost nhưng nâng accuracy từ 4,35% lên 91,30%; sửa hai
     mục KB đưa accuracy lên 100% và giảm cost trên mỗi câu đúng.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Thêm synthetic check qua Nginx để thấy lỗi 502/504 mà metric trong agent không
ghi được; alert theo burn rate của error budget ở nhiều cửa sổ thời gian; và
quality gate theo dataset cập nhật từ phản hồi người dùng. Các đề xuất này
chưa được triển khai trong lab.
