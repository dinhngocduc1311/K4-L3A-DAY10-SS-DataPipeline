# Báo Cáo Nhóm — Day 10 Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
|---|---|
| Khóa/lớp | K4-L3A |
| Tên nhóm | SS |
| Thành viên | Đinh Ngọc Đức (2A202602935), Nguyễn Việt Thành (2A202602924) |
| Repository | https://github.com/dinhngocduc1311/K4-L3A-DAY10-SS-DataPipeline |
| Ngày nghiệm thu | 2026-09-25 |

Phân công chi tiết và danh sách file không trùng nhau được ghi tại docs/TEAM.md.

## 2. Tóm tắt kết quả

Nhóm đã hoàn thiện pipeline dữ liệu bài báo Crossref theo hai luồng baseline và corruption/repair. Luồng baseline bảo toàn raw response, chuẩn hóa 24 bản ghi, loại JATS XML, tính age_days, tạo text_for_embedding, chạy Quality Gate Great Expectations 1.x, nạp MiniLM embeddings vào ChromaDB và đánh giá bằng bộ 10 câu hỏi cố định. Luồng thử thách tiêm đủ sáu dạng lỗi, khiến Quality Gate và Freshness SLA cùng thất bại, Retrieval Hit Rate giảm từ 100% xuống 20% và Mean Token F1 giảm từ 1.000 xuống 0.733. Repair không vá dữ liệu lỗi tại chỗ mà tái tạo từ raw source, sau đó xác minh các cột trọng yếu khớp baseline; cả hai chỉ số phục hồi hoàn toàn. Ba collection Chroma tách biệt và cơ chế upsert/delete stale IDs giúp chạy lại không sinh collection rác. OpenRouter đã được cấu hình với Gemini 3.5 Flash, nhưng tài khoản không đủ credit cho toàn bộ LLM Judge; lần nghiệm thu cuối dùng mock và ghi rõ judge_mode=heuristic_fallback để không giả mạo kết quả.

## 3. Kiến trúc và trách nhiệm

Crossref API hoặc snapshot offline → raw records → cleaning → GX/Freshness → MiniLM/Chroma → benchmark → corruption → re-index/evaluate → repair từ raw → báo cáo ba trạng thái.

| Khối | Input | Xử lý | Output | Owner |
|---|---|---|---|---|
| Ingestion | Crossref/snapshot | Retry, parse DOI/JATS/date | data/raw | Đinh Ngọc Đức |
| Cleaning | Raw records | Normalize, dedupe, age_days | data/clean | Đinh Ngọc Đức |
| Embedding/index | Clean dataframe | all-MiniLM-L6-v2, Chroma upsert | data/chroma | Đinh Ngọc Đức |
| Evaluation | Index + test set | Hit Rate, Token F1, Judge | data/results | Đinh Ngọc Đức |
| QA/Observability | Questions/dataframe | Agent, GX 1.x, freshness | data/quality | Nguyễn Việt Thành |
| Corruption/repair | Baseline + raw | 6 lỗi, rebuild từ raw | comparison artifacts | Nguyễn Việt Thành |

## 4. Cấu hình và tái hiện

| Cấu hình | Giá trị |
|---|---|
| Python | 3.12.9 |
| LLM provider mặc định | openrouter |
| LLM model | google/gemini-3.5-flash |
| Validation mode của artifacts hiện tại | mock / heuristic_fallback do thiếu OpenRouter credit |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Crossref records | 24 |
| Retrieval top_k | 4 |
| Freshness threshold | 180 ngày; tối đa 25% stale |

Lệnh cài đặt:

    python -m pip install -e .

Lệnh chạy:

    python script/run_phase1.py
    python script/run_corruption_flow.py

Hai lệnh đã chạy exit code 0 trong lần nghiệm thu bằng mock. Khi OpenRouter có đủ credit, chạy lại hai lệnh không đặt LLM_PROVIDER=mock để cập nhật Judge thật.

## 5. Data contract và cleaning

Raw schema gồm paper_id, title, summary, authors, categories, primary_category, published, updated, abs_url, pdf_url và comment. DOI được chuẩn hóa chữ thường; title/summary được chuẩn hóa khoảng trắng; summary được loại HTML/JATS; ngày được parse ISO 8601. Clean flow bỏ record thiếu paper_id/title/summary, bỏ DOI trùng, tính age_days và ghép năm phần Title, Authors, Published, Categories, Summary vào text_for_embedding.

Crossref dùng tối đa hai lần retry cho 429/503. Khi API mất mạng, quá tải hoặc trả thiếu 24 DOI duy nhất, pipeline dùng data/raw/crossref_response.json và vẫn lưu data/raw/crossref_records.json để bảo toàn lineage.

## 6. Evaluation setup

Test set cố định có 10 câu đúng docs gốc:

| Loại | Số câu |
|---|---:|
| summary | 3 |
| authors | 2 |
| date | 2 |
| categories | 3 |

Mỗi mẫu có id, type, question_type, question, ground_truth và ground_truth_doc_ids. Cùng một file data/eval/test_set.json được dùng cho baseline, corrupted và repaired để so sánh công bằng.

## 7. Quality và freshness

GX chạy bằng ephemeral context và sáu validation instance thuộc bốn expectation bắt buộc: row count, not-null cho ba cột trọng yếu, unique paper_id và summary tối thiểu 30 ký tự.

| Trạng thái | GX | Freshness | Stale |
|---|---|---|---:|
| Baseline | PASS (6/6) | PASS | 1/24 = 4.17% |
| Corrupted | FAIL (4/6) | FAIL | 13/24 = 54.17% |
| Repaired | PASS (6/6) | PASS | 1/24 = 4.17% |

## 8. Corruption và repair

| Kịch bản | Số dòng tác động | Mô phỏng |
|---|---:|---|
| Drop latest records | 5 | Mất 20% dữ liệu mới nhất |
| Blank summary | 3 | Thiếu nội dung |
| Inject text noise | 5 | Summary và embedding bị nhiễu |
| Truncate title | 3 | Tiêu đề còn tối đa 7 ký tự |
| Stale date | 8 | Ngày bị lùi 5 năm |
| Duplicate rows | 5 | Trùng paper_id |

Repair đọc lại data/raw/crossref_records.json, chạy lại cleaning, kiểm tra paper_id/title/summary/published/text_for_embedding khớp baseline, rồi build collection papers-repaired. Không có thao tác sửa tay artifact.

## 9. So sánh ba trạng thái

| Metric/signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval Hit Rate | 100.00% | 20.00% | 100.00% |
| Mean Token F1 | 1.0000 | 0.7329 | 1.0000 |
| Judge Accuracy | 100.00% | 80.00% | 100.00% |
| Mean Judge Score | 5.00/5 | 3.60/5 | 5.00/5 |
| Judge mode | heuristic_fallback | heuristic_fallback | heuristic_fallback |
| Quality Gate | PASS | FAIL | PASS |
| Freshness | PASS | FAIL | PASS |

Kết luận nhân quả:

1. Drop, blank/noise và title truncation làm mất hoặc làm sai tín hiệu truy vấn, khiến Hit Rate giảm 80 điểm phần trăm và Token F1 giảm 0.2671.
2. Stale date cộng duplicate rows làm tỷ lệ stale tăng từ 4.17% lên 54.17%, vượt SLA 25%.
3. Rebuild từ raw source loại toàn bộ corruption, đưa Quality/Freshness và metrics trở lại đúng baseline.

## 10. Vấn đề tích hợp và giới hạn

- Chroma ban đầu xóa/tạo lại collection và để lại segment mồ côi. Nhóm chuyển sang get-or-create, upsert và chỉ xóa stale IDs; số segment giữ ổn định ở ba collection.
- Gemini 3.5 Flash mặc định dành nhiều token cho reasoning. Client đã đặt reasoning_effort=minimal và max_tokens=300.
- OpenRouter key hợp lệ nhưng credit hiện không đủ cho 30 lượt Judge của hai flow. Artifacts dùng fallback có nhãn; cần nạp credit và chạy lại nếu yêu cầu Judge thật.
- Ragas là tùy chọn và đang tắt; Hit Rate, Token F1 và Judge vẫn được xuất đầy đủ.

## 11. Artifact checklist

- data/raw/crossref_response.json và crossref_records.json: có.
- data/clean/papers_clean.csv và JSON: có.
- data/chroma với ba collection, mỗi collection 24 tài liệu: có.
- data/eval/test_set.json gồm 10 câu: có.
- data/results baseline/corrupted/repaired metrics và corruption log: có.
- data/quality baseline/corrupted/repaired và freshness: có.
- data/reports/phase1_report.md và corruption_report.md: có.
- docs/TEAM.md và hai báo cáo cá nhân: có.

## 12. Việc còn lại trước khi nộp

- Mỗi thành viên tự commit đúng tập file được phân công.
- Merge/push toàn bộ lên nhánh main và kiểm tra cả hai thành viên trong Insights → Contributors.
- Bổ sung email vào docs/TEAM.md nếu giảng viên yêu cầu.
- Nạp OpenRouter credit và chạy lại nếu muốn judge_mode=llm.
- Mỗi thành viên tự nộp link repository lên VLearn.
