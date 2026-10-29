# PNJ Trade-in Checker

App Streamlit giúp tư vấn viên tra cứu và tính cấn trừ thu đổi theo **PL A2 (hiệu lực 30/09/2026)** và **TB 442-2026 (28/09/2026)**.

## Chạy
```
pip install -r requirements.txt
streamlit run app.py
pytest -q
```

## Dùng app
1. Thanh bên: chọn cửa hàng HUB/thường, ngày giờ giao dịch, các điều kiện giao dịch, và nhập giá vàng/Platin (nhập tay, mặc định 0).
2. Tab **Tính cấn trừ** chia 2 cột: **Hàng cũ (Bảng kê)** bên trái, **Hàng mới (Hóa đơn)** bên phải. Mỗi dòng gồm nhóm hàng, giá trị, nút ⚙️ (dòng hàng, ngày hóa đơn, giá nguyên liệu) và nút Xóa; có nút thêm món và tổng giá trị dưới mỗi cột. Bên dưới là kết quả: tỷ lệ Thu/Đổi, giá trị cấn trừ, phương án 1/2/3, nơi thực hiện, khung giờ, lộ trình chi trả, chứng từ và gợi ý câu trả lời. Không có món hàng mới nghĩa là khách chỉ bán lại.
3. Tab **Quy trình**, **Ma trận & thanh toán**, **Q&A**: tra cứu nhanh.

## Cấu trúc
```
app.py            giao diện
tradein/          logic: rules, matrix, kc, calc, scripts
data/rules.yaml   tỷ lệ Thu/Đổi theo dòng hàng (kèm căn cứ)
data/matrix.yaml  nhóm hàng, ma trận chuyển đổi, lộ trình thanh toán
data/faq.yaml     quy trình và Q&A
tests/            pytest + AppTest
SPEC.md, tasks/   spec, kế hoạch
```

## Cập nhật khi có văn bản mới
Chỉ sửa file trong `data/` (và `documents` trong `matrix.yaml`), rồi chạy `pytest`. Không sửa tỷ lệ trong code.

## Giới hạn của v1 (xem SPEC.md mục 10)
- Chỉ tính luồng sản phẩm nguyên hiện trạng. Mất đá/mất chi tiết/hao hụt TL, chênh lệch do sửa chữa, đơn đặt cọc: xem tab Quy trình.
- Không tự xác định đá chính từ mã SP/BOM; tư vấn viên chọn hình dáng, độ sạch, cỡ.
- Không biết hạn mức (quota) còn lại, giá vàng, danh sách HUB.
- Đúng giá trị biên giữa hai dòng (ví dụ 4ly): app lấy giá trị thấp hơn và cảnh báo; cần P. Vận hành bán lẻ xác nhận.
- Dòng cần PL A8, A11, A12, A14, A15, A16 hoặc quyết định duyệt: app nhắc tra phụ lục, không tự tính.
