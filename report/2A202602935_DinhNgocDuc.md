# Báo Cáo Cá Nhân — Đinh Ngọc Đức

## 1. Thông tin

| Thuộc tính | Nội dung |
|---|---|
| Họ tên | Đinh Ngọc Đức |
| MSSV | 2A202602935 |
| Vai trò | Nhóm trưởng; Data Foundation, Vector Index & Baseline |

## 2. Phạm vi sở hữu

Tôi chịu trách nhiệm độc quyền các file sau để không conflict với Nguyễn Việt Thành:

- src/core/config.py, src/core/utils.py
- src/ingestion/crossref.py, src/ingestion/cleaning.py
- src/retrieval/embeddings.py, src/retrieval/index.py
- src/evaluation/__init__.py, src/evaluation/testset.py, src/evaluation/metrics.py
- src/pipelines/phase1.py, script/run_phase1.py

## 3. Công việc và kết quả

| Nhiệm vụ | Kết quả | Bằng chứng |
|---|---|---|
| Cấu hình hệ thống | Centralized paths; OpenRouter/Gemini 3.5 Flash | src/core/config.py |
| Crossref ingestion | DOI/date/JATS parsing; retry và offline fallback | data/raw |
| Cleaning | 24 dòng unique; age_days; embedding text 5 phần | data/clean |
| Vector index | MiniLM, Chroma idempotent, 24 docs/collection | data/chroma |
| Benchmark | 10 câu, 4 loại theo docs gốc | data/eval/test_set.json |
| Baseline | Hit Rate 100%, Token F1 1.000 | baseline_metrics.json |

## 4. Giải thích kỹ thuật

Raw response được giữ nguyên để bảo đảm lineage. Parser chuẩn hóa DOI, loại HTML/JATS bằng HTMLParser và chuyển ngày về ISO 8601. Cleaning loại record thiếu trường trọng yếu, deduplicate bằng paper_id, tính tuổi dữ liệu theo UTC và ghép Title, Authors, Published, Categories, Summary cho embedding.

Chroma dùng get-or-create và upsert thay cho delete/create. ID cũ không còn trong dataframe được xóa riêng, nhờ đó chạy lại không sinh segment mồ côi. Benchmark dùng cùng ground-truth document IDs ở cả ba trạng thái.

## 5. Quyết định kỹ thuật quan trọng

Tôi ưu tiên docs gốc: test set gồm 10 câu với summary, authors, date và categories. Phân bố 3/2/2/3 là gần cân bằng nhất vì 10 không chia hết cho 4. Ba câu categories dùng bài mới nhất để đo trực tiếp tác động của kịch bản drop latest.

## 6. Lỗi đã xử lý

- API Crossref có thể 429/mất mạng: tự động dùng snapshot và vẫn tạo đủ 24 raw records.
- Chroma delete/create để lại thư mục rác: thay bằng upsert và stale-ID cleanup.
- OpenRouter mặc định xin output quá lớn: đặt max_tokens=300 và reasoning_effort=minimal.
- OpenRouter thiếu credit trong lần nghiệm thu: giữ fallback có judge_mode rõ ràng, không ghi số LLM giả.

## 7. Hiểu luồng end-to-end

Baseline nhận raw source, làm sạch, kiểm tra chất lượng, index, chạy benchmark và ghi metrics/report. Corruption flow của Thành dùng đúng test set này để đánh giá dữ liệu lỗi, sau đó repair từ raw records và so sánh lại. Contract tích hợp chính là paper_id ổn định, schema clean thống nhất và đường dẫn lấy từ Settings.

## 8. Phân tích số liệu

Baseline đạt Hit Rate 100%, Token F1 1.000, GX 6/6 và stale ratio 4.17%. Corruption làm Hit Rate còn 20% và Token F1 còn 0.7329. Repaired trở lại đúng baseline, chứng minh raw preservation và idempotent rebuild hoạt động.

## 9. Điều học được

1. Raw lineage quan trọng hơn vá thủ công dữ liệu đã hỏng.
2. Benchmark phải cố định mới so sánh ba trạng thái công bằng.
3. Idempotence phải bao gồm cả dữ liệu lẫn storage vật lý.

## 10. Cam kết

Tôi hiểu các file được phân công, có thể chạy và giải thích baseline flow. Tôi sẽ tự commit đúng tập file này, merge lên main và không commit .env hoặc API key.
