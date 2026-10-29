# Spec: PNJ Trade-in Checker (Streamlit)

> Trạng thái: **v1 đã triển khai** theo các giả định mặc định ở mục 0 và mục 10 (xem `tasks/plan.md`). Các mục chưa làm được ghi rõ ở mục 7 và README.
> Ngày soạn: 29/10/2026. Căn cứ: 4 tài liệu nguồn ở mục 1.

## 0. Giả định đang áp dụng (sửa ngay nếu sai)

1. Đây là **một app Streamlit** (không phải di động/native), dùng nội bộ bởi tư vấn viên (TVV) tại cửa hàng.
2. App **chỉ tra cứu và tính toán theo quy định**, không kết nối SAP/mPos/ERP: không biết quota thực tế, không biết giá vàng, không lập chứng từ.
3. Quy tắc (tỷ lệ, nhóm hàng, lộ trình) nằm trong **file dữ liệu có phiên bản**, không viết cứng trong code.
4. Phiên bản quy định áp dụng: **Phụ lục A2 (hiệu lực 30/09/2026)** + **Thông báo 442-2026-TB (28/09/2026)**. Hai văn bản này là nguồn chuẩn; Excel và ảnh chỉ để đối chiếu.
5. Hệ nhóm hàng chuẩn của app là **nhóm thanh toán 1–13** (PDF/Excel), vì khớp văn bản mới nhất. Nhóm chính sách 1–9 của A2 được ánh xạ sang (xem 2.3).
6. "Giá trị hàng cũ" khi so sánh điều kiện "hàng mới ≥ hàng cũ" là **giá trị theo hóa đơn cũ** (ví dụ trong A2: HĐ cũ 100 triệu, HĐ mới 105 triệu → đủ điều kiện).
7. Không lưu dữ liệu cá nhân khách hàng. Dữ liệu nhập chỉ nằm trong phiên làm việc.
8. v1 gồm luồng chuẩn (sản phẩm nguyên hiện trạng). Các trường hợp không nguyên hiện trạng, chênh lệch do sửa chữa, đơn đặt cọc hiển thị dưới dạng **hướng dẫn tra cứu**, chưa tự tính.

## 1. Objective

### 1.1 Tài liệu nguồn

| ID | Tài liệu | Số hiệu / hiệu lực | Vai trò |
|---|---|---|---|
| SRC-A2 | Phụ lục A2: Quy định chính sách thu đổi (.docx) | MS PNJ-QT-PVHBL-TĐHTK-A2, LSX 5, hiệu lực 30/09/2026 | Tỷ lệ Thu/Đổi, điều kiện, xử lý SP không nguyên hiện trạng |
| SRC-TB442 | Thông báo thay đổi thời gian thanh toán (.pdf) | 442-2026-TB-P.VHBL-TĐTGTTHML-PNJ, ngày 28/09/2026, áp dụng từ 30/09/2026 đến khi có thông báo mới; thay thế TB 346-2026 | HUB, khung giờ, phương án 1/2/3, nhóm thanh toán, lộ trình T+2/T+7/T+120 |
| SRC-MAP | Hướng dẫn Mapping (.xlsx) | Không có số hiệu | Gộp A2 + TB442 theo nhóm thanh toán 1–13 |
| SRC-IMG | Ảnh ma trận nhóm N#…N^ (.jpg) | Không có số hiệu/ngày | Ma trận nhóm cũ → nhóm mới theo mã N |

Lưu ý: 442-2026 là **Thông báo (TB)**, không phải Quyết định. Banner của app nên ghi "TB 442-2026".

### 1.2 Mục tiêu

Giúp TVV, trong vài chục giây, trả lời được cho khách hàng thu đổi:
1. Món hàng cũ thuộc nhóm nào, được **Thu** hay **Đổi**, tỷ lệ bao nhiêu (theo ngày xuất hóa đơn).
2. Khách có được **chuyển đổi** sang nhóm hàng mới đang chọn không, và số tiền **cấn trừ** là bao nhiêu.
3. Nếu có tiền phải chi trả cho khách: làm ở HUB hay cửa hàng thường, khung giờ nào, **lộ trình thanh toán** thế nào, cần chứng từ gì.
4. Gợi ý câu trả lời để TVV nói với khách, kèm căn cứ văn bản.

Người dùng: tư vấn viên bán hàng (chính), kế toán trưởng chi nhánh/quản lý (phụ).
Thành công nghĩa là: kết quả của app **khớp với ví dụ minh họa trong A2** và TVV không phải mở văn bản để tra tỷ lệ.

## 2. Hiểu tài liệu (tóm tắt)

### 2.1 Hai lớp quy tắc

| Lớp | Câu hỏi | Nguồn |
|---|---|---|
| A. Thu đổi | Hàng cũ được tính giá bao nhiêu (tỷ lệ Thu/Đổi hoặc theo giá nguyên liệu)? | SRC-A2 |
| B. Thanh toán chuyển đổi | Nếu phát sinh chi tiền cho khách thì chi ở đâu, khi nào, theo lộ trình nào? | SRC-TB442 |

- **Thu** = mua lại hàng cũ (tỷ lệ thấp hơn). **Đổi** = đổi sang hàng mới (tỷ lệ cao hơn).
- **Điều kiện được hưởng Đổi** (A2 §2.2): nhóm cũ và mới đều thuộc nhóm được áp dụng đổi; tổng giá trị hàng mới ≥ tổng giá trị hàng cũ; mã khách hàng trên Bảng kê (BKTMHHMVKCHĐ) và HĐ mới là một. Nếu không đạt (hoặc bán lại không mua mới) → áp dụng **Thu**.
- **Sản phẩm nguyên hiện trạng**: không biến dạng, không mất chi tiết, đúng cấp chất lượng, dấu đóng rõ, trọng lượng lệch trong ±0,006 chỉ so với HĐ/hệ thống.
- **Chứng từ**: HĐ do PNJ phát hành, chính sách bán hàng, giấy giám định đá (nếu có). Thiếu chứng từ nhưng nhận diện được hàng PNJ → xử lý theo từng trường hợp.

### 2.2 Phương án của khách (TB442 mục III)

| Phương án | Nội dung | Làm ở đâu |
|---|---|---|
| 1 | Chuyển đổi toàn bộ sang hàng mới có giá trị ≥ giá trị mua lại | HUB và cửa hàng thường |
| 2 | Chuyển đổi một phần, phần còn lại nhận tiền theo lộ trình của dòng hàng | Chỉ HUB |
| 3 | Mua lại hoàn toàn | Chỉ HUB |

- PA1 và PA2 chỉ áp dụng khi nhóm hàng thuộc diện được chuyển đổi thanh toán; nếu không thì chỉ còn PA3.
- Bất kỳ giao dịch nào phát sinh nghĩa vụ chi tiền cho khách đều coi là **Mua Lại** và bắt buộc làm tại **HUB**.
- Khung giờ nhận giao dịch Mua Lại: **15h00–17h00**, 17h00 ngừng phát số.
- Hạn mức tiền mặt cấp mỗi đầu ngày theo dòng hàng và chi nhánh, không bổ sung trong ngày; KTT chi nhánh ngừng nhận khi hết hạn mức.
- Chỉ in **Phụ lục 01 Thỏa thuận thu đổi sản phẩm** khi áp dụng PA2 (2 bản: khách giữ 1, cửa hàng lưu 1). Bảng kê Mẫu 02/TNDN luôn đi kèm.

### 2.3 Bảng ánh xạ nhóm hàng

| Nhóm chính sách (A2) | Nhóm thanh toán (TB442/Excel) | Dòng hàng | Mã trong ảnh |
|---|---|---|---|
| (không có) | 1 | Vàng miếng, nhẫn khoen, vàng Phúc Lộc Tài, vàng Kim Bảo | N# |
| 1 | 2 | TS kim cương, đá màu, ngọc trai (gồm chuỗi), TS vỏ, mua theo mã dùng chung; không gồm Style | N1 |
| 2 | 3 | TS công nghệ Ý (gắn KC), TS KGĐ/dây chuyền, ECZ/CZ/đá tổng hợp, mua theo mã nguyên liệu PNJ; không gồm Style | N2 |
| 3 | 4 | Tuổi vàng 91,6% / 99% / 99,1–99,9% / 99,99%; quà tặng sưu tầm | N3 |
| 4 | 5 | KC rời, đá màu rời, ngọc trai rời, vòng cẩm thạch | N4 |
| 5 | 6 | Style by PNJ: TS kim cương, đá màu, ngọc trai | N5 |
| 6 | 7 | Style by PNJ: TS KGĐ/dây chuyền, ECZ/CZ/đá tổng hợp | N6 |
| 7 | 8 | Heart2Heart (PL A12) | N7 |
| 8 | 9 | Kind Heart | N8 |
| 9 | 10 | Vòng/lắc charm phong thủy đặc biệt, bao lì xì phong thủy (PL A11) | N9 |
| (không có) | 11 | Nguyên liệu non-PNJ | |
| (không có) | 12 | SP kênh KHDN PNJ kinh doanh (PL A15) | |
| (không có) | 13 | SP kênh KHDN PNJP kinh doanh (PL A16) | |

Nhóm thanh toán = nhóm chính sách + 1 (từ nhóm 2 trở đi). Excel đã viết lại số nhóm theo cách này (ví dụ "Nhóm 4 đổi qua nhóm 2,3"). Ảnh còn có N0, N4P, N9P, N^ mà A2/TB442 không có.

### 2.4 Ma trận chuyển đổi (hàng cũ → hàng mới, theo nhóm thanh toán)

Đã đối chiếu A2, Excel và PDF: **ba nguồn khớp nhau**.

| Nhóm cũ | Được chuyển đổi sang nhóm mới |
|---|---|
| 1 | 2, 3, 4, 5, 6, 7 |
| 2 | 2, 5 |
| 3 | 2, 3, 5 |
| 4 | 2, 3, 4, 5 |
| 5 | 2, 5 |
| 6 | 6 |
| 7 | 6, 7 |
| 8 | 8 |
| 9 | 9 |
| 10 | 10 |
| 11, 12, 13 | Không áp dụng chuyển đổi thanh toán |

### 2.5 Lộ trình thanh toán theo nhóm

| Nhóm thanh toán | Thời gian | Lộ trình |
|---|---|---|
| 1 | T+2 | 100% T+2 |
| 3, 4, 7, 8, 9, 10, 11, 12, 13 | T+7 | 100% T+7 |
| 2, 5, 6 | T+120 | 10% T/T+1; 20% T+30; 25% T+60; 25% T+90; 20% T+120 |

Giao dịch T+120 đã xác lập trước đó: nhóm 1, 3, 4, 7, 8, 9, 10 được chi trả toàn bộ phần còn lại; nhóm 2, 5, 6 giữ nguyên lộ trình đã thỏa thuận (TB442 mục V).

### 2.6 Công thức giá nguyên liệu (A2 §2.1)

- Thu theo giá NL: vàng = TLV × **giá mua vào** vàng nữ trang theo tuổi (bảng giá điện tử tại thời điểm thu đổi). Platin = TL × đơn giá NL Platin.
- Đổi theo giá NL: vàng = TLV × **giá bán ra** theo tuổi. Platin như trên.
- Đơn giá NL Platin = đơn giá Platin chuẩn (quy 10) hiện hành × tuổi Platin (ví dụ A2: 7.000.000 đ/chỉ → Platin 9000 = 6.300.000, 9500 = 6.650.000).
- Đơn giá Platin hao hụt = giá bán ra vàng 999.9 × tuổi Platin (ví dụ: 17.000.000 × 95% = 16.150.000).
- Đá: KC từ 3,5ly trở lên theo giá P.MH định giá; KC dưới 3,5ly theo PL A8.
- Dung sai trọng lượng ±0,006 chỉ: trong dung sai thì lấy TL trên HĐ; vượt thì lấy TL thực tế.

### 2.7 Xác định đá chính (A2 mục Định nghĩa)

1. Loại đá chính = ký tự thứ 3–4 của mã SP.
2. Với SP có BOM đá: chọn các mã đá có ký tự 1–2 trùng ký tự 3–4 của mã SP; trong đó chọn đá có **cạnh lớn** lớn nhất, hòa thì xét **cạnh nhỏ**.
3. Không có BOM: chuyển P.TL&ĐBCL và P.MH xác định.
4. TSKC "Fancy" = đá chính có hình dáng bất kỳ trừ hình tròn.

Ví dụ A2: SP `GVDDMXW000006.520` → loại "DD" (TSKC); các đá STT 1, 3, 4 thỏa điều kiện 1; STT 1 (5,4×5,4) có cạnh lớn nhất → đá chính; là KC trắng tròn → TSKC trắng tròn.

### 2.8 Bảng tỷ lệ (bản đọc hiểu để đối chiếu)

Quy ước: ghi `Thu / Đổi` cho **HĐ xuất bán trước 05/01/2026**. Cột "Từ 05/01/2026" là quy tắc cho HĐ từ ngày đó. "NL" = theo giá nguyên liệu.

| Nhóm A2 | Dòng hàng | Thu / Đổi (trước 05/01/2026) | Từ 05/01/2026 | Ghi chú |
|---|---|---|---|---|
| 1 | TS KC: tròn IF/FL/VVS1/VS1 ≤4ly; tròn VVS2…KQT mọi cỡ; KC màu | 80% / 90% | Không đổi | Đổi sang combo mới (TS vỏ + KCR) tổng ≥ hàng cũ: Đổi 85% |
| 1 | TS KC trắng Fancy ≤3,5ly | 80% / 90% | Không đổi | |
| 1 | TS KC trắng Fancy ≥3,5ly | 75% / 85% | Không đổi | |
| 1 | TS KC tròn IF/FL/VVS1/VS1 ≥4ly | Vỏ 80% / 85%; viên theo tỷ lệ KCR | Không đổi | Ví dụ A2: HĐ 100tr (vỏ 20tr, viên 80tr, KC 4,5ly VVS1), mua mới 105tr → vỏ 17tr + viên 76tr = **93tr** |
| 1 | TS đá màu | 75% / 85% | Không đổi | |
| 1 | TS ngọc trai nước ngọt | 50% / 70% | Vàng Thu NL; ngọc trai không thu đổi | |
| 1 | TS ngọc trai nước mặn | 60% / 75% | Không đổi | |
| 1 | TS ngọc trai Mother of Pearl | Thu NL / Đổi NL | Vàng Thu NL; ngọc trai không thu đổi | |
| 1 | Chuỗi ngọc trai gắn khóa vàng | 55% / 60% | Không đổi | HĐ trước 15/01/2016 theo cam kết trên HĐ; không nguyên hiện trạng: khóa vàng Thu NL |
| 1 | Chuỗi ngọc trai nước ngọt không khóa vàng | Không thu mua | Không thu mua | |
| 1 | Chuỗi ngọc trai nước mặn không khóa vàng | <20tr/SP: không thu; ≥20tr: 50% | Không đổi | Không nguyên hiện trạng/thiếu chứng từ: không thu mua |
| 1 | TS vỏ | 80% / 85% | Không đổi | |
| 2 | TS công nghệ Ý gắn KC | 80% / 90% | Thu NL | |
| 2 | TS KGĐ, dây chuyền các loại, TS công nghệ Ý | 70% / 80% | Thu NL | |
| 2 | TS CZ/ECZ/đá tổng hợp | 70% / 80% | HĐ 05/01–31/03/2026: khách chọn tỷ lệ 70/80 **hoặc** Thu theo giá NL & mã NL. HĐ từ 01/04/2026: tỷ lệ 70/80 | |
| 3 | Tuổi vàng 91,6 / 99 / 99,1–99,9 / 99,99 (giá bán = công + vàng, hoặc giá bán món) | Thu NL; Đổi: xem quy tắc nhóm 3 bên dưới | Thu NL; SP gắn đá thì thu đổi 50% giá trị đá | |
| 3 | Quà tặng sưu tầm, giá bán = công + vàng | Thu NL / Thu NL | Thu NL | PL A14 |
| 3 | Quà tặng sưu tầm, giá bán món | 70% / 80% | Thu NL | PL A14 |
| 4 | KC trắng tròn VS1/VVS1↑ ≥10ly | Không thu lại | Không thu lại | |
| 4 | KC trắng tròn VS1/VVS1↑ 8,6–10ly | ≤1 năm 93%; >1 năm 90% | Không đổi | HĐ trước 11/06/2018 theo cam kết trên HĐ |
| 4 | KC trắng tròn VS1/VVS1↑ 6–8,6ly | 95% / 98% | Không đổi | |
| 4 | KC trắng tròn VS1/VVS1↑ 5–6ly | 93% / 97% | Không đổi | |
| 4 | KC trắng tròn VS1/VVS1↑ <5ly | 93% / 95% | Không đổi | |
| 4 | KC trắng tròn SI ≥6ly | 90% / 95% | Không đổi | |
| 4 | KC trắng tròn SI <6ly | 85% / 90% | Không đổi | |
| 4 | KC màu | 80% / 90% | Không đổi | Chỉ SP bán trước 23/07/2023 hoặc được duyệt theo tờ trình |
| 4 | Đá màu rời | <2tr/viên: không thu; ≥2tr: 70% giá trị HĐ | Không đổi | |
| 4 | Ngọc trai rời nước ngọt, Mabe | Không thu mua | Không đổi | |
| 4 | Ngọc trai rời nước mặn | <3tr/viên: không thu; ≥3tr: 70% giá trị HĐ | Không đổi | |
| 4 | Vòng cẩm thạch | <8tr/SP: không thu; ≥8tr: 50% giá trị HĐ | Không đổi | |
| 5 | Style by PNJ: TS KC, đá màu, ngọc trai | 50% / 60% | Không đổi | Sau 1 năm kể từ ngày xuất bán: Thu NL |
| 6 | Style by PNJ: TS CZ/ECZ/đá tổng hợp, KGĐ, dây chuyền | 50% / 60% | Không đổi | Sau 1 năm: Thu NL |
| 7 | Heart2Heart | Thu NL | Không đổi | PL A12 |
| 8 | Kind Heart | Thu NL | Không đổi | HĐ trước 01/10/2024 theo cam kết trên HĐ |
| 9 | Vòng/lắc charm phong thủy đặc biệt | 65% / 75% | Thu NL | PL A11 |
| 9 | Bao lì xì phong thủy | Không thu mua | Không thu mua | |
| KHDN | PNJ / PNJP kinh doanh kênh KHDN | Theo PL A15 / A16 | | Không có trong tài liệu |

Quy tắc Đổi của nhóm 3 (HĐ trước 05/01/2026):
- Nhóm 3 đổi sang nhóm 1 hoặc 2 (nhóm thanh toán 2–3): toàn bộ TLV cũ **Đổi theo giá NL**.
- Nhóm 3 đổi cùng nhóm 3: nếu TLV mới < TLV cũ thì phần TLV chênh lệch **Thu NL**, phần còn lại Đổi NL; nếu TLV mới ≥ TLV cũ thì toàn bộ TLV cũ Đổi NL. (Ví dụ A2: cũ 10 chỉ, mới 9 chỉ → 9 chỉ Đổi NL + 1 chỉ Thu NL.)

### 2.9 Các tài liệu được dẫn chiếu nhưng chưa có

PL A1, A4, A8 (bảng giá thu mua KC tấm, phí mài), A11, A12, A14, A15, A16; Phụ lục 01 (mẫu); danh sách HUB; Q&A và luồng vận hành (link "TẠI ĐÂY"); TB 140-2025 (mã nguyên liệu); danh sách Kind Heart.

## 3. Tech Stack

- Python 3.11+, Streamlit (phiên bản chốt khi vào Plan).
- Dữ liệu quy tắc: YAML/CSV trong repo, kiểm tra bằng schema (pydantic).
- Tính tiền: `decimal.Decimal`, không dùng float.
- Kiểm thử: pytest. Định dạng/lint: ruff.
- Môi trường người dùng: Microsoft 365 (cách triển khai và xác thực: xem Open Questions).

## 4. Commands (giả định, chốt khi có repo)

```
Dev:    streamlit run app.py
Test:   pytest -q --cov=tradein
Lint:   ruff check . --fix && ruff format .
Verify: python -m tradein.verify_rules   # đối chiếu dữ liệu quy tắc với ma trận nguồn
```

## 5. Project Structure (đề xuất)

```
app.py                  → Streamlit, 4 tab: Cấn trừ / Quy trình / Ma trận & thanh toán / Q&A
tradein/
  rules/                → loader + schema
  classify.py           → xác định nhóm, đá chính, Fancy/tròn
  pricing.py            → Thu/Đổi, giá nguyên liệu, cấn trừ
  payment.py            → phương án, HUB, khung giờ, lộ trình
  scripts.py            → gợi ý câu trả lời cho TVV
data/
  rules_a2.yaml         → tỷ lệ Thu/Đổi (kèm nguồn: văn bản, mục, dòng)
  conversion_matrix.yaml
  payment_schedule.yaml
  sources.yaml          → số hiệu, ngày hiệu lực, trạng thái
tests/                  → unit + golden tests từ ví dụ trong A2
docs/                   → tài liệu nguồn, SPEC.md
```

## 6. Code Style

Quy tắc là dữ liệu, mỗi quy tắc mang theo căn cứ văn bản.

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class RatioRule:
    rule_id: str                 # "A2-G1-KC-TRON-GE4-VVS1"
    policy_group: int            # 1..9 (A2)
    payment_group: int           # 1..13 (TB442)
    thu: Decimal | str           # Decimal("0.80") | "GIA_NL" | "KHONG_THU"
    doi: Decimal | str
    source: str                  # "A2 §2.3, dòng 'TS KC tròn ≥4ly'"

def doi_value(invoice_value: Decimal, rule: RatioRule) -> Decimal:
    if not isinstance(rule.doi, Decimal):
        raise NeedsMaterialPricing(rule.rule_id)   # cần giá vàng/NL do người dùng nhập
    return (invoice_value * rule.doi).quantize(Decimal("1"))
```

Quy ước: tên module/hàm tiếng Anh, chuỗi hiển thị và chú thích nghiệp vụ tiếng Việt, tiền tệ VND làm tròn đến đồng.

## 7. Testing Strategy

- **Golden tests từ ví dụ trong A2** (bắt buộc đạt 100%):
  - KC 4,5ly VVS1, HĐ 100tr (vỏ 20tr, viên 80tr), mua mới 105tr → 93.000.000 đ. *(đã có test)*
  - Platin: đơn giá chuẩn 7.000.000 → NL Platin 9000 = 6.300.000, 9500 = 6.650.000. *(đã có test)*
  - Nhóm 3 A2 đổi cùng nhóm: cũ 10 chỉ, mới 9 chỉ → 9 chỉ Đổi NL + 1 chỉ Thu NL. *(đã có test)*
  - Chưa làm ở v1: ví dụ Platin hao hụt (17.000.000 × 95% = 16.150.000) và ví dụ đá chính của `GVDDMXW000006.520`, vì cả hai nằm ngoài phạm vi v1 (hao hụt TL, đá chính theo mã SP/BOM).
- **Test ma trận**: ma trận chuyển đổi trong `data/` khớp bảng 2.4; có test đối chiếu với file Excel nguồn.
- **Test ngày hiệu lực**: các mốc 05/01/2026, 31/03/2026, 01/04/2026, 11/06/2018, 23/07/2023, 01/10/2024, 15/01/2016.
- **Test biên**: giá trị đúng bằng 4ly, 3,5ly, 5ly, 6ly, 8,6ly, 10ly; đúng 2tr/3tr/8tr/20tr.
- **Test payment**: HUB/không HUB, trong/ngoài 15h–17h, PA1/2/3, nhóm không đủ điều kiện chuyển đổi.
- Kiểm thử giao diện: thủ công theo checklist, chưa tự động ở v1.

## 8. Boundaries

- **Luôn làm**: ghi căn cứ (văn bản, mục) bên cạnh mỗi kết quả; hiển thị ngày hiệu lực và số hiệu văn bản; chạy test trước khi commit; dùng Decimal.
- **Hỏi trước**: thêm thư viện; đổi cấu trúc file dữ liệu quy tắc; kết nối hệ thống ngoài (SAP, mPos, Supabase); lưu bất kỳ dữ liệu khách hàng nào.
- **Không bao giờ**: viết cứng tỷ lệ trong code; tự suy diễn khi văn bản mơ hồ (phải hiện cảnh báo và chuyển P.TL&ĐBCL / Vận hành bán lẻ); lưu thông tin cá nhân khách; commit secret/API key; tự khẳng định số liệu hạn mức/quota hay giá vàng khi chưa được nhập.

## 9. Success Criteria

1. Tra được tỷ lệ Thu/Đổi cho mọi dòng hàng trong bảng 2.8 theo ngày xuất HĐ.
2. Ma trận chuyển đổi và lộ trình thanh toán trong app **trùng khớp** bảng 2.4 và 2.5; có test tự động.
3. Cả 4 golden test ở mục 7 đạt.
4. Với một giao dịch mẫu, app cho ra: nhóm cũ/mới, được Đổi hay chỉ Thu, số tiền cấn trừ, phương án khả dụng, nơi thực hiện (HUB hay không), khung giờ, lộ trình thanh toán.
5. Mọi kết quả đều kèm trích dẫn nguồn; trường hợp không tự tính được hiển thị rõ lý do và bước tiếp theo.
6. Có banner số hiệu và ngày hiệu lực; khi cập nhật văn bản mới chỉ cần thay file trong `data/` mà không sửa code.
7. TVV mới làm được một lượt tra cứu hoàn chỉnh trong dưới 60 giây (kiểm tra thủ công với 3 người dùng thử).

## 10. Open Questions

Mặc định ghi trong ngoặc sẽ được dùng nếu bạn không phản hồi.

1. **Ảnh ma trận N#…N^ có phải bản cũ không?** Theo cách tôi đọc ảnh, nó khác văn bản mới ở 2 chỗ: (a) hàng "Vàng miếng" chỉ chuyển được sang N0, N5, N6, trong khi PDF/Excel cho nhóm 2–7; (b) hàng KCR (N4) thu đổi chỉ thấy N1, trong khi A2/Excel cho cả nhóm 1 và 4. Ảnh còn có các mã N0, N4P, N9P, N^ không có trong A2/TB442. (Mặc định: coi ảnh là bản cũ/tham khảo, dùng A2 + TB442.)
2. **Hệ nhóm hiển thị trong app**: số 1–13 hay mã N#…N^? (Mặc định: 1–13; có cột đối chiếu mã N nếu bạn cần.)
3. **Ranh giới kích thước bị chồng lấn** trong A2: "≤4ly" và "từ 4ly↑"; "≤3,5ly" và "từ 3,5ly↑"; 5ly, 6ly, 8,6ly, 10ly ở bảng KCR; SI "↓6ly" và "6ly↑". Đúng bằng giá trị biên thì áp dụng dòng nào? (Mặc định: dòng có tỷ lệ **thấp hơn**, kèm cảnh báo biên.)
4. **"Kích thước lớn nhất"** là cạnh lớn của đá chính (mm = ly)? (Mặc định: có.)
5. **Nhập liệu**: TVV chọn từ danh sách (loại đá, hình dáng, độ sạch, cỡ) hay nhập mã SP/BOM để app tự xác định đá chính theo 2.7? (Mặc định: chọn từ danh sách; thuật toán đá chính làm ở v1.1.)
6. **Giá đầu vào**: giá mua vào/bán ra vàng theo tuổi, đơn giá Platin chuẩn, giá P.MH định giá, bảng A8: nhập tay, hay có nguồn dữ liệu? (Mặc định: nhập tay trên giao diện.)
7. **Mốc so sánh "hàng mới ≥ hàng cũ"**: A2 so với tổng giá trị HĐ cũ; TB442 (PA1) nói "≥ giá trị mua lại". Hai mốc này có khác nhau không? (Mặc định: dùng giá trị theo HĐ cũ như ví dụ A2.)
8. **"10% T/T + 1"** trong lộ trình T+120 nghĩa là trả ngày giao dịch (T) hay T+1? (Mặc định: hiển thị đúng nguyên văn "T/T+1" và ghi chú cần xác nhận.)
9. **Phạm vi v1**: có cần tự tính các trường hợp không nguyên hiện trạng (mất đá, mất chi tiết, hao hụt TL), chênh lệch do sửa chữa, đơn đặt cọc không? (Mặc định: không, chỉ hướng dẫn tra cứu.)
10. **Danh sách HUB** (link "TẠI ĐÂY" chưa có): app có cần biết cửa hàng hiện tại là HUB không? (Mặc định: TVV tự chọn HUB/không HUB.)
11. **Gợi ý câu trả lời cho khách**: dùng mẫu câu soạn sẵn theo từng tình huống, hay có AI sinh câu trả lời? (Mặc định: mẫu câu soạn sẵn, có trích dẫn nguồn.)
12. **Triển khai và xác thực**: chạy ở đâu (máy chủ nội bộ, Streamlit Community Cloud, Azure) và ai được truy cập? (Mặc định: chưa quyết, chốt ở bước Plan.)
13. **Dữ liệu quy tắc để trong repo** hay trong Supabase/SharePoint? (Mặc định: trong repo, dạng YAML.)
14. **Tài liệu còn thiếu** ở mục 2.9: bạn có thể cung cấp PL A8, A11, A12, A14, A15, A16 và danh sách HUB không?
