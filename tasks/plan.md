# Implementation Plan: PNJ Trade-in Checker (Streamlit)

Căn cứ: `SPEC.md` (đã chốt các giả định mặc định ở mục 0 và mục 10).

## Overview
App Streamlit tra cứu và tính cấn trừ thu đổi theo PL A2 (hiệu lực 30/09/2026) và TB 442-2026.
Quy tắc nằm trong `data/*.yaml`; logic trong `tradein/`; giao diện trong `app.py`.

## Architecture Decisions
- Quy tắc là dữ liệu (YAML) kèm căn cứ văn bản; code không chứa tỷ lệ.
- `Decimal` cho mọi phép tính tiền.
- Ranh giới kích thước đá trùng nhau: tính cả hai dòng và lấy giá trị thấp hơn (mặc định đã nêu trong SPEC).
- Giá vàng/Platin nhập tay trên sidebar; không có giá thì không tính dòng theo giá nguyên liệu.
- Không lưu dữ liệu khách hàng.

## Task List
### Phase 1: Foundation (dữ liệu + quy tắc)
- [x] T1: `data/rules.yaml`, `data/matrix.yaml`, loader + resolve theo ngày HĐ (`tradein/rules.py`, `tradein/matrix.py`)
- [x] T2: xác định dòng KC theo đặc điểm đá, xử lý ranh giới (`tradein/kc.py`)
### Checkpoint: Foundation
- [x] pytest: loader, ma trận, ranh giới

### Phase 2: Tính toán
- [x] T3: cấn trừ từng món + giá nguyên liệu + dung sai (`tradein/calc.py`)
- [x] T4: điều kiện Đổi, phương án 1/2/3, chi trả, HUB, khung giờ, lộ trình (`tradein/calc.py`)
- [x] T5: gợi ý câu trả lời cho TVV (`tradein/scripts.py`)
### Checkpoint: Core
- [x] Golden tests từ ví dụ A2 đạt

### Phase 3: Giao diện
- [x] T6: `app.py` 4 tab: Tính cấn trừ / Quy trình / Ma trận & thanh toán / Q&A
### Checkpoint: Complete
- [x] AppTest chạy không lỗi

## Risks
| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Văn bản mơ hồ (ranh giới cỡ đá, "T/T+1", mốc so sánh ≥) | Cao | Cảnh báo trên giao diện, ghi vào Open Questions |
| Thiếu PL A8/A11/A12/A14/A15/A16 | Trung bình | Dòng liên quan trả về "tra phụ lục", không tự tính |
| Giá nhập tay sai | Trung bình | Không có giá mặc định; hiển thị giá đã dùng trong kết quả |
