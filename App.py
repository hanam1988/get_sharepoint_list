"""
Ứng dụng hỗ trợ tư vấn viên kiểm tra THU ĐỔI trang sức/vàng và gợi ý câu trả lời cho khách.

Chạy:
    pip install streamlit pandas
    streamlit run app.py

LƯU Ý: Các tỷ lệ khấu trừ/phí mặc định bên dưới chỉ là GIÁ TRỊ MẪU.
Hãy chỉnh lại theo chính sách thu đổi thực tế của công ty (thanh bên trái, mục "Chính sách").
Kết quả chỉ mang tính tham khảo, giá trị cuối cùng theo thẩm định tại quầy.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tư vấn thu đổi", page_icon="💍", layout="wide")

GRAM_PER_CHI = 3.75

PURITY = {
    "Vàng 24K (9999)": 0.9999,
    "Vàng 24K (999)": 0.999,
    "Vàng 18K (750)": 0.750,
    "Vàng 14K (585)": 0.585,
    "Vàng 10K (416)": 0.416,
}

# Kịch bản -> % khấu trừ mặc định trên giá trị vàng (CHỈNH THEO CHÍNH SÁCH THỰC TẾ)
SCENARIOS = {
    "Vàng miếng / nhẫn trơn 9999": 0.0,
    "Trang sức mua tại cửa hàng, có hóa đơn, còn nguyên vẹn": 5.0,
    "Trang sức mua tại cửa hàng, không còn hóa đơn": 10.0,
    "Trang sức mua nơi khác (cần giám định)": 15.0,
}

CONDITIONS = {
    "Còn mới / nguyên vẹn": 0.0,
    "Trầy xước nhẹ": 1.0,
    "Móp méo / biến dạng": 3.0,
    "Gãy / hư hỏng nặng (thu theo nguyên liệu)": 6.0,
}


def vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " đ"


# ---------------------------------------------------------------- Sidebar
with st.sidebar:
    st.header("⚙️ Giá & chính sách")
    gold_price_chi = st.number_input(
        "Giá thu mua vàng 24K hôm nay (đ/chỉ)",
        min_value=0,
        value=7_500_000,
        step=10_000,
        help="Nhập giá thu mua niêm yết trong ngày.",
    )
    st.caption(f"≈ {vnd(gold_price_chi / GRAM_PER_CHI)}/gram")

    with st.expander("Chính sách (chỉnh được)", expanded=False):
        scenario_pct = {
            k: st.number_input(f"% trừ – {k}", 0.0, 100.0, v, 0.5, key=f"s_{k}")
            for k, v in SCENARIOS.items()
        }
        condition_pct = {
            k: st.number_input(f"% trừ – {k}", 0.0, 100.0, v, 0.5, key=f"c_{k}")
            for k, v in CONDITIONS.items()
        }
        fixed_fee = st.number_input("Phí cố định (giám định/nấu), đ", 0, value=0, step=10_000)
        stone_pct_default = st.slider("% giá trị đá/kim cương thu lại", 0, 100, 30)
        exchange_bonus_pct = st.number_input(
            "Ưu đãi khi ĐỔI sang sản phẩm mới (% cộng thêm trên giá trị thu)",
            0.0, 50.0, 0.0, 0.5,
            help="Để 0 nếu không có chương trình. Nhập theo chương trình đang áp dụng.",
        )
        uncertainty = st.slider("Biên độ ước tính (±%)", 0, 10, 2)

# ---------------------------------------------------------------- Main
st.title("💍 Kiểm tra thu đổi cho khách")
st.caption("Nhập thông tin sản phẩm khách mang đến → xem giá trị ước tính và gợi ý câu trả lời.")

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("1. Thông tin sản phẩm cũ")
    customer = st.text_input("Tên khách (không bắt buộc)")
    scenario = st.selectbox("Nguồn gốc / giấy tờ", list(SCENARIOS))
    purity_name = st.selectbox("Tuổi vàng", list(PURITY))
    c1, c2 = st.columns(2)
    total_weight = c1.number_input("Tổng trọng lượng (gram)", 0.0, value=3.75, step=0.01, format="%.2f")
    stone_weight = c2.number_input("Trọng lượng đá/hột (gram)", 0.0, value=0.0, step=0.01, format="%.2f")
    condition = st.selectbox("Tình trạng", list(CONDITIONS))

    has_stone = st.checkbox("Có đá / kim cương")
    stone_original = 0
    stone_pct = stone_pct_default
    if has_stone:
        stone_original = st.number_input("Giá trị đá khi mua (đ) – nếu biết", 0, value=0, step=100_000)
        stone_pct = st.slider("% giá trị đá thu lại", 0, 100, stone_pct_default, key="stone_pct_main")

    st.subheader("2. Nhu cầu của khách")
    need = st.radio("Khách muốn", ["Bán lại (thu)", "Đổi sang sản phẩm mới"], horizontal=True)
    new_price = 0
    if need.startswith("Đổi"):
        new_price = st.number_input("Giá sản phẩm mới khách quan tâm (đ)", 0, value=0, step=100_000)

# ---------------------------------------------------------------- Tính toán
gold_weight = max(total_weight - stone_weight, 0.0)
price_per_g = gold_price_chi / GRAM_PER_CHI
purity = PURITY[purity_name]
gold_raw = gold_weight * purity * price_per_g

deduct_pct = scenario_pct[scenario] + condition_pct[condition]
gold_net = max(gold_raw * (1 - deduct_pct / 100) - fixed_fee, 0.0)
stone_value = stone_original * stone_pct / 100 if has_stone else 0.0

base_value = gold_net + stone_value
bonus = base_value * exchange_bonus_pct / 100 if need.startswith("Đổi") else 0.0
total_value = base_value + bonus

low = total_value * (1 - uncertainty / 100)
high = total_value * (1 + uncertainty / 100)
difference = new_price - total_value if need.startswith("Đổi") and new_price else None

with right:
    st.subheader("3. Kết quả ước tính")
    m1, m2 = st.columns(2)
    m1.metric("Giá trị thu đổi ước tính", vnd(total_value))
    m2.metric("Khoảng tham khảo", f"{vnd(low)} – {vnd(high)}")

    if difference is not None:
        if difference > 0:
            st.info(f"Khách bù thêm khoảng **{vnd(difference)}** cho sản phẩm mới.")
        else:
            st.success(f"Giá trị thu đổi đã vượt giá sản phẩm mới khoảng **{vnd(-difference)}**.")

    with st.expander("Chi tiết cách tính", expanded=True):
        st.markdown(
            f"""
- Trọng lượng vàng: {total_weight:.2f} − {stone_weight:.2f} = **{gold_weight:.2f} g**
- Tuổi vàng quy đổi: **{purity:.4f}** → vàng nguyên chất ≈ {gold_weight * purity:.3f} g
- Giá trị vàng theo giá thu mua: **{vnd(gold_raw)}**
- Khấu trừ: nguồn gốc {scenario_pct[scenario]:.1f}% + tình trạng {condition_pct[condition]:.1f}% = **{deduct_pct:.1f}%**
- Phí cố định: {vnd(fixed_fee)}
- Vàng sau khấu trừ: **{vnd(gold_net)}**
- Giá trị đá thu lại: **{vnd(stone_value)}**
- Ưu đãi khi đổi: **{vnd(bonus)}**
"""
        )

    # ------------------------------------------------------------ Gợi ý trả lời
    st.subheader("4. Gợi ý trả lời khách")

    warnings, scripts = [], []

    if total_weight <= 0:
        warnings.append("Chưa nhập trọng lượng – hãy cân sản phẩm trước khi báo giá.")
    if stone_weight >= total_weight > 0:
        warnings.append("Trọng lượng đá lớn hơn hoặc bằng tổng trọng lượng – kiểm tra lại số liệu.")
    if scenario.endswith("(cần giám định)") or "không còn hóa đơn" in scenario:
        warnings.append("Sản phẩm thiếu hóa đơn / nguồn gốc – cần kiểm tra, giám định trước khi chốt giá.")
    if has_stone and stone_original == 0:
        warnings.append("Có đá nhưng chưa có giá trị gốc – giá đá cần thẩm định tại quầy.")
    if "Gãy" in condition or "Móp" in condition:
        warnings.append("Sản phẩm hư hỏng/biến dạng – giá có thể thấp hơn khách kỳ vọng, nên giải thích trước.")

    scripts.append(
        (
            "Mở đầu",
            f"Dạ, với sản phẩm anh/chị mang đến, em ước tính giá trị thu đổi khoảng "
            f"{vnd(low)} – {vnd(high)}. Giá cuối cùng sẽ được xác nhận sau khi cân và kiểm tra trực tiếp tại quầy ạ.",
        )
    )

    if deduct_pct > 0:
        scripts.append(
            (
                "Khi khách hỏi vì sao thấp hơn giá vàng niêm yết",
                "Dạ, giá niêm yết là cho vàng nguyên liệu 24K. Sản phẩm của mình là vàng "
                f"{purity_name.split('(')[0].strip().lower()} và đã qua chế tác nên được quy đổi theo tuổi vàng, "
                "đồng thời trừ các chi phí xử lý theo chính sách thu đổi ạ.",
            )
        )

    if has_stone:
        scripts.append(
            (
                "Về phần đá / kim cương",
                "Dạ, phần đá sẽ được thẩm định riêng theo kích thước, màu sắc, độ sạch và giấy kiểm định (nếu có). "
                "Anh/chị mang theo giấy kiểm định giúp em thì giá sẽ chính xác hơn ạ.",
            )
        )

    if need.startswith("Đổi"):
        bonus_text = (
            f" Ngoài ra khi đổi sang sản phẩm mới, mình còn được cộng thêm ưu đãi {exchange_bonus_pct:.1f}% giá trị thu ạ."
            if exchange_bonus_pct > 0
            else ""
        )
        scripts.append(
            (
                "Khuyến khích đổi sang sản phẩm mới",
                "Dạ, nếu mình đổi sang sản phẩm mới, toàn bộ giá trị thu đổi sẽ được trừ trực tiếp vào giá sản phẩm mới, "
                f"anh/chị chỉ cần bù phần chênh lệch ạ.{bonus_text}",
            )
        )
        if difference is not None and difference > 0:
            scripts.append(
                (
                    "Khi khách thấy phần bù hơi nhiều",
                    f"Dạ, phần chênh lệch hiện khoảng {vnd(difference)}. Nếu anh/chị muốn, em có thể gợi ý thêm vài mẫu "
                    "có trọng lượng hoặc mức giá gần hơn với giá trị đang có để mình bù ít hơn ạ.",
                )
            )
    else:
        scripts.append(
            (
                "Khi khách chỉ muốn bán",
                "Dạ, em có thể thu lại ngay hôm nay theo giá đã báo. Nếu sau này anh/chị có nhu cầu mua mới, "
                "mình vẫn có thể đổi để tận dụng giá trị sản phẩm cũ ạ.",
            )
        )

    scripts.append(
        (
            "Khi khách muốn chờ giá tốt hơn",
            "Dạ, giá vàng thay đổi theo ngày nên giá em báo là theo giá hôm nay. Anh/chị cứ giữ lại cũng được, "
            "khi nào cần mình mang đến, em sẽ kiểm tra lại theo giá lúc đó ạ.",
        )
    )

    for w in warnings:
        st.warning(w)
    for title, text in scripts:
        with st.expander(f"💬 {title}"):
            st.write(text)
            st.code(text, language=None)

# ---------------------------------------------------------------- Lịch sử
if "history" not in st.session_state:
    st.session_state.history = []

st.divider()
if st.button("💾 Lưu lượt tư vấn này"):
    st.session_state.history.append(
        {
            "Thời gian": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Khách": customer,
            "Tuổi vàng": purity_name,
            "TL vàng (g)": round(gold_weight, 2),
            "Nguồn gốc": scenario,
            "Tình trạng": condition,
            "Nhu cầu": need,
            "Giá trị ước tính (đ)": round(total_value),
            "Chênh lệch khách bù (đ)": round(difference) if difference is not None else "",
        }
    )
    st.success("Đã lưu.")

if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    st.subheader("Lịch sử phiên làm việc")
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "⬇️ Tải CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="lich_su_thu_doi.csv",
        mime="text/csv",
    )

st.caption("⚠️ Kết quả mang tính tham khảo. Giá cuối cùng theo thẩm định và chính sách tại quầy.")