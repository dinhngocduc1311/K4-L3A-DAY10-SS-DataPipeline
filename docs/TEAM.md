# Danh Sách Thành Viên & Phân Công Nhóm

- **Tên nhóm:** SS
- **Mã nhóm / lớp:** K4-L3A-DAY10
- **Repository:** K4-L3A-DAY10-SS-DataPipeline

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò |
|---:|---|---|---|---|
| 1 | Đinh Ngọc Đức | 2A202602935 | Chưa cung cấp | Nhóm trưởng; Data Foundation, Vector Index & Baseline |
| 2 | Nguyễn Việt Thành | 2A202602924 | Chưa cung cấp | QA Agent, Observability, Corruption & Repair |

## Quy tắc chống conflict

Hai thành viên chỉ sửa và commit các file thuộc phạm vi của mình. Mọi thay đổi contract dùng chung được thống nhất trước khi code; không cùng sửa một file trên hai nhánh.

### Đinh Ngọc Đức — 2A202602935

**Phạm vi code độc quyền:**

- src/core/config.py, src/core/utils.py
- src/ingestion/crossref.py, src/ingestion/cleaning.py
- src/retrieval/embeddings.py, src/retrieval/index.py
- src/evaluation/__init__.py, src/evaluation/testset.py, src/evaluation/metrics.py
- src/pipelines/phase1.py, script/run_phase1.py

**Deliverables:**

- Cấu hình provider, model và toàn bộ đường dẫn artifact.
- Ingestion Crossref có retry và offline fallback; chuẩn hóa raw records.
- Làm sạch, tính age_days, khử trùng và tạo text_for_embedding.
- MiniLM embeddings, ChromaDB idempotent, benchmark 10 câu và baseline metrics.
- Điều phối baseline pipeline và kiểm chứng artifacts Pha 1.

### Nguyễn Việt Thành — 2A202602924

**Phạm vi code độc quyền:**

- src/ingestion/corruption.py
- src/retrieval/__init__.py, src/retrieval/agent.py, src/retrieval/llm.py, src/retrieval/qa.py
- src/observability/__init__.py, src/observability/quality.py, src/observability/reporting.py
- src/pipelines/corruption_flow.py, script/run_corruption_flow.py

**Deliverables:**

- Multi-provider QA Agent và router OpenRouter/Gemini.
- Quality Gate GX 1.x, Freshness SLA và báo cáo Markdown.
- Sáu kịch bản corruption, nhật ký lỗi và đo suy giảm.
- Repair từ raw source, kiểm tra khớp baseline và báo cáo ba trạng thái.

## Contract tích hợp

- Hai luồng dùng chung schema do PaperRecord và clean dataframe định nghĩa.
- Evaluation dùng cố định data/eval/test_set.json cho cả ba trạng thái.
- Đức bàn giao baseline artifacts trước; Thành chỉ chạy corruption flow sau khi baseline pass.
- Mỗi thành viên tự commit các file thuộc danh sách của mình và phải xuất hiện trên GitHub main.
