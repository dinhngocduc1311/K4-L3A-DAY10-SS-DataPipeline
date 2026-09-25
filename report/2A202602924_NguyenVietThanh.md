# Báo Cáo Cá Nhân — Nguyễn Việt Thành

## 1. Thông tin

| Thuộc tính | Nội dung |
|---|---|
| Họ tên | Nguyễn Việt Thành |
| MSSV | 2A202602924 |
| Vai trò | QA Agent, Observability, Corruption & Repair |

## 2. Phạm vi sở hữu

Tôi chịu trách nhiệm độc quyền các file sau để không conflict với Đinh Ngọc Đức:

- src/ingestion/corruption.py
- src/retrieval/__init__.py, src/retrieval/agent.py, src/retrieval/llm.py, src/retrieval/qa.py
- src/observability/__init__.py, src/observability/quality.py, src/observability/reporting.py
- src/pipelines/corruption_flow.py, script/run_corruption_flow.py

## 3. Công việc và kết quả

| Nhiệm vụ | Kết quả | Bằng chứng |
|---|---|---|
| QA Agent | Semantic search, exact lookup, multi-provider router | src/retrieval |
| Quality Gate | GX 1.x, bốn expectation, freshness SLA | data/quality |
| Corruption | Đủ 6 lỗi và log paper IDs | corruption_log.json |
| Repair | Rebuild từ raw, xác minh khớp baseline | repaired artifacts |
| Reporting | Báo cáo baseline và ba trạng thái | data/reports |

## 4. Giải thích kỹ thuật

Quality Gate dùng GX ephemeral context, kiểm tra row count, not-null, unique paper_id và summary tối thiểu 30 ký tự. Freshness tính tỷ lệ age_days lớn hơn 180 và fail nếu vượt 25%.

Corruption giữ tổng số dòng ở 24 để so sánh công bằng: bỏ 5 bài mới nhất rồi nhân đôi 5 dòng, đồng thời blank summary, chèn noise, cắt title tối đa 7 ký tự và lùi ngày xuất bản 365 ngày. Repair không sửa dataframe lỗi mà chạy lại cleaning từ raw source, kiểm tra các cột trọng yếu khớp baseline rồi tạo collection riêng.

## 5. Quyết định kỹ thuật quan trọng

Sáu lỗi được tiêm deterministic để chạy lại cho cùng kết quả. Noise được đưa vào summary rồi tái tạo text_for_embedding, đáp ứng cả corruption nội dung và corruption vector input. Dữ liệu corrupted vẫn được index để minh họa Silent Failure, nhưng quality/freshness status được lưu rõ trong báo cáo.

## 6. Lỗi đã xử lý

- GX API cũ không tương thích 1.x: dùng data_sources.add_pandas và whole-dataframe batch definition.
- Duplicate rows làm Chroma ID xung đột: record_id ghép paper_id với row index.
- Freshness chỉ sai ngày nhưng age_days không đổi: corruption cập nhật đồng thời published và age_days.
- Repair có thể trông đúng nhưng sai nội dung: so sánh paper_id, title, summary, published và text_for_embedding với baseline.

## 7. Hiểu luồng end-to-end

Tôi nhận baseline artifacts và test set do Đức bàn giao. Corruption flow tạo dataframe lỗi, chạy quality/freshness, build papers-corrupted và đánh giá. Sau đó flow đọc raw records, rebuild papers-repaired, chạy lại cùng checks/test set và sinh corruption_report.md.

## 8. Phân tích số liệu

Corrupted GX chỉ pass 4/6 và stale ratio tăng lên 54.17%, nên cả Quality Gate và Freshness đều fail. Hit Rate giảm từ 100% xuống 20%; Token F1 giảm từ 1.000 xuống 0.7329. Repair đưa GX về 6/6, stale ratio về 4.17% và hai retrieval/answer metrics trở lại baseline.

## 9. Điều học được

1. Data quality pass/fail phải gắn với tác động retrieval định lượng.
2. Dữ liệu bẩn vẫn có thể cho câu trả lời trôi chảy, tạo Silent Failure.
3. Repair từ nguồn raw đáng tin cậy an toàn hơn vá theo từng triệu chứng.

## 10. Cam kết

Tôi hiểu các file được phân công, có thể chạy và giải thích corruption/repair flow. Tôi sẽ tự commit đúng tập file này, merge lên main và không commit .env hoặc API key.
