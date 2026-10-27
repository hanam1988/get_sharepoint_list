"""
PNJ - Hệ thống tra cứu & hướng dẫn thu đổi chuyển đổi (Streamlit)

Chạy:
    pip install streamlit pandas
    streamlit run app.py

LƯU Ý QUAN TRỌNG
- Toàn bộ nhóm hàng, hệ số cấn trừ, ma trận mapping, cách xử lý phần dư, các bước quy trình và
  câu hỏi đáp bên dưới là DỮ LIỆU MẪU. Hãy thay bằng nội dung thật trong quyết định / Phụ lục A2.
- Có thể sửa trực tiếp trong tab 3 (lưu trong phiên làm việc), hoặc sửa hằng số ở đầu file để cố định.
"""

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PNJ - Tra cứu & hướng dẫn thu đổi", page_icon="💎", layout="wide")

# =============================================================== CẤU HÌNH (DỮ LIỆU MẪU)
POLICY_TITLE = "PNJ - HỆ THỐNG TRA CỨU & HƯỚNG DẪN THU ĐỔI CHUYỂN ĐỔI"
POLICY_REF = "Áp dụng theo QĐ 442-2026-TB-P.VHBL-TĐTGTTHML-PNJ & PL A2 (Hiệu lực từ 30/09/2026)"

PLACEHOLDER = "-- Chọn nhóm hàng --"
GROUP_COL = "Nhóm hàng"
COEF_COL = "Hệ số cấn trừ (%)"
LEFTOVER_COL = "Xử lý phần dư không cấn trừ hết"
MATRIX_KEY = "Hàng cũ ↓ / Hàng mới →"

DEFAULT_GROUPS = [
    # (Nhóm hàng, hệ số cấn trừ %, cách xử lý phần dư)  <- THAY BẰNG SỐ LIỆU THẬT
    ("Vàng miếng 9999", 100, "Hoàn tiền / thanh toán lại cho khách"),
    ("Nhẫn trơn, vàng 24K", 100, "Hoàn tiền / thanh toán lại cho khách"),
    ("Trang sức vàng 18K/14K/10K", 95, "Giữ lại làm số dư cấn trừ lần sau"),
    ("Trang sức đính đá", 90, "Giữ lại làm số dư cấn trừ lần sau"),
    ("Kim cương / trang sức kim cương", 85, "Giữ lại làm số dư cấn trừ lần sau"),
    ("Trang sức bạc", 80, "Hoàn tiền / thanh toán lại cho khách"),
]

# Hàng cũ -> các nhóm hàng mới được phép cấn trừ  <- THAY THEO PL A2
DEFAULT_ALLOWED = {
    "Vàng miếng 9999": ["Vàng miếng 9999", "Nhẫn trơn, vàng 24K", "Trang sức vàng 18K/14K/10K",
                        "Trang sức đính đá", "Kim cương / trang sức kim cương"],
    "Nhẫn trơn, vàng 24K": ["Nhẫn trơn, vàng 24K", "Trang sức vàng 18K/14K/10K",
                            "Trang sức đính đá", "Kim cương / trang sức kim cương"],
    "Trang sức vàng 18K/14K/10K": ["Trang sức vàng 18K/14K/10K", "Trang sức đính đá",
                                   "Kim cương / trang sức kim cương"],
    "Trang sức đính đá": ["Trang sức vàng 18K/14K/10K", "Trang sức đính đá",
                          "Kim cương / trang sức kim cương"],
    "Kim cương / trang sức kim cương": ["Trang sức đính đá", "Kim cương / trang sức kim cương"],
    "Trang sức bạc": ["Trang sức vàng 18K/14K/10K", "Trang sức bạc"],
}

PROCESS_CUSTOMER = [
    "Mang sản phẩm cũ (kèm hóa đơn/giấy kiểm định nếu còn) đến quầy.",
    "Nhân viên kiểm tra, cân và lập bảng kê hàng cũ cùng khách.",
    "Khách xác nhận giá trị hàng cũ và chọn sản phẩm mới.",
    "Hệ thống xác định phần được cấn trừ và phần khách thanh toán thêm.",
    "Khách thanh toán phần chênh lệch (nếu có), nhận hóa đơn và sản phẩm mới.",
]
PROCESS_STAFF = [
    "Tiếp nhận, kiểm tra tình trạng và nguồn gốc sản phẩm cũ.",
    "Lập bảng kê (BK) từng món: nhóm hàng, giá trị.",
    "Lập hóa đơn (HĐ) sản phẩm mới cho khách.",
    "Nhập BK và HĐ ở tab 1 để xác định cấn trừ và phương án thanh toán.",
    "Giải thích cho khách các khoản được trừ, phần dư và phần phải thanh toán thêm.",
    "Hoàn tất chứng từ và lưu trữ theo quy định.",
]
PAYMENT_ROUTE = [
    "**Bước 1 – Xác định nhóm hàng** của từng món cũ (BK) và món mới (HĐ).",
    "**Bước 2 – Áp hệ số cấn trừ** theo nhóm hàng cũ.",
    "**Bước 3 – Mapping** giá trị cấn trừ vào các món mới được phép (theo ma trận bên dưới).",
    "**Bước 4 – Thanh toán**: khách trả phần còn lại của hóa đơn mới; phần dư xử lý theo từng nhóm.",
]

FAQS = [
    ("Vì sao giá trị cấn trừ thấp hơn giá trị trên bảng kê?",
     "Mỗi nhóm hàng cũ có hệ số cấn trừ riêng. Giá trị cấn trừ = giá trị bảng kê × hệ số của nhóm hàng đó."),
    ("Hàng cũ của tôi có cấn trừ được vào mọi sản phẩm mới không?",
     "Không phải mọi trường hợp. Mỗi nhóm hàng cũ chỉ được cấn trừ vào một số nhóm hàng mới nhất định (xem tab 3)."),
    ("Nếu giá trị hàng cũ lớn hơn hàng mới thì phần dư xử lý thế nào?",
     "Phần dư được xử lý theo từng nhóm hàng (ví dụ hoàn tiền hoặc giữ lại làm số dư). Xem cột xử lý phần dư ở tab 3."),
    ("Cần mang theo giấy tờ gì khi thu đổi?",
     "Nên mang hóa đơn, giấy kiểm định (nếu có) và giấy tờ tùy thân. Cập nhật danh sách giấy tờ theo quy định hiện hành."),
    ("Phần chênh lệch thanh toán bằng hình thức nào?",
     "Theo các hình thức thanh toán đang áp dụng tại cửa hàng. Cập nhật theo quy định hiện hành."),
]


# =============================================================== TIỆN ÍCH
def vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " VNĐ"


def default_groups_df() -> pd.DataFrame:
    return pd.DataFrame(DEFAULT_GROUPS, columns=[GROUP_COL, COEF_COL, LEFTOVER_COL])


def default_matrix_df() -> pd.DataFrame:
    names = [g[0] for g in DEFAULT_GROUPS]
    rows = []
    for old in names:
        row = {MATRIX_KEY: old}
        for new in names:
            row[new] = new in DEFAULT_ALLOWED.get(old, [])
        rows.append(row)
    return pd.DataFrame(rows)


ss = st.session_state
ss.setdefault("old_ids", [1])
ss.setdefault("new_ids", [1])
ss.setdefault("next_id", 2)
if "groups_df" not in ss:
    ss.groups_df = default_groups_df()
if "matrix_df" not in ss:
    ss.matrix_df = default_matrix_df()


def add_row(kind: str):
    ss[f"{kind}_ids"].append(ss.next_id)
    ss.next_id += 1


def del_row(kind: str, rid: int):
    ids = ss[f"{kind}_ids"]
    if len(ids) > 1:
        ids.remove(rid)
    else:  # còn đúng 1 dòng thì chỉ xóa nội dung
        ss[f"{kind}_grp_{rid}"] = PLACEHOLDER
        ss[f"{kind}_val_{rid}"] = 0


def render_rows(kind: str, prefix: str, options: list[str]) -> list[dict]:
    items = []
    for i, rid in enumerate(ss[f"{kind}_ids"], start=1):
        c1, c2, c3 = st.columns([3, 2.2, 1])
        grp = c1.selectbox(f"Món {prefix}{i}:", options, key=f"{kind}_grp_{rid}")
        val = c2.number_input(f"Giá trị {prefix}{i} (VNĐ):", min_value=0, step=100_000, key=f"{kind}_val_{rid}")
        c3.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        c3.button("🗑️ Xóa", key=f"{kind}_del_{rid}", on_click=del_row, args=(kind, rid))
        items.append({"label": f"{prefix}{i}", "group": grp, "value": float(val)})
    return items


def allocate(old_items, new_items, groups_df, matrix_df):
    """Cấn trừ giá trị hàng cũ vào hàng mới theo hệ số và ma trận mapping."""
    coef = dict(zip(groups_df[GROUP_COL], groups_df[COEF_COL]))
    leftover_rule = dict(zip(groups_df[GROUP_COL], groups_df[LEFTOVER_COL]))
    matrix = matrix_df.set_index(MATRIX_KEY)

    remaining = {n["label"]: n["value"] for n in new_items}
    alloc_rows, old_rows = [], []

    for o in old_items:
        credit_full = o["value"] * float(coef.get(o["group"], 100)) / 100
        haircut = o["value"] - credit_full
        left = credit_full
        for n in new_items:
            if left <= 0:
                break
            allowed = bool(matrix.loc[o["group"], n["group"]]) if o["group"] in matrix.index and n["group"] in matrix.columns else False
            if not allowed or remaining[n["label"]] <= 0:
                continue
            amt = min(left, remaining[n["label"]])
            remaining[n["label"]] -= amt
            left -= amt
            alloc_rows.append({
                "Hàng cũ": f'{o["label"]} – {o["group"]}',
                "Cấn trừ vào": f'{n["label"]} – {n["group"]}',
                "Số tiền cấn trừ": amt,
            })
        old_rows.append({
            "Hàng cũ": f'{o["label"]} – {o["group"]}',
            "Giá trị bảng kê": o["value"],
            "Giảm do hệ số": haircut,
            "Phần dư không cấn trừ được": left,
            "Xử lý phần dư": leftover_rule.get(o["group"], ""),
        })

    applied = sum(r["Số tiền cấn trừ"] for r in alloc_rows)
    new_total = sum(n["value"] for n in new_items)
    return {
        "alloc_rows": alloc_rows,
        "old_rows": old_rows,
        "applied": applied,
        "new_total": new_total,
        "pay_more": new_total - applied,
        "haircut": sum(r["Giảm do hệ số"] for r in old_rows),
        "unused": sum(r["Phần dư không cấn trừ được"] for r in old_rows),
    }


def build_suggestions(r: dict) -> list[tuple[str, str]]:
    if not r.get("has_data"):
        return [("Chưa có dữ liệu", "Hãy nhập hàng cũ (BK) và hàng mới (HĐ) ở tab 1 để nhận gợi ý trả lời khách.")]
    out = [(
        "Báo kết quả tổng quan",
        f"Dạ, tổng giá trị hàng cũ theo bảng kê là {vnd(r['old_total'])}. Sau khi áp dụng quy định cấn trừ, "
        f"giá trị được trừ vào hóa đơn mới là {vnd(r['applied'])} ạ.",
    )]
    if r["new_total"] > 0:
        if r["pay_more"] > 0:
            out.append((
                "Phần khách thanh toán thêm",
                f"Dạ, hóa đơn mới là {vnd(r['new_total'])}, sau khi cấn trừ anh/chị thanh toán thêm {vnd(r['pay_more'])} ạ.",
            ))
        else:
            out.append((
                "Cấn trừ đủ, không phải trả thêm",
                "Dạ, giá trị hàng cũ đủ để cấn trừ toàn bộ hóa đơn mới nên anh/chị không phải thanh toán thêm ạ.",
            ))
    if r["haircut"] > 0:
        out.append((
            "Khi khách hỏi vì sao thấp hơn giá trị bảng kê",
            f"Dạ, mỗi nhóm hàng cũ có hệ số cấn trừ riêng theo quy định, nên giá trị cấn trừ giảm {vnd(r['haircut'])} "
            "so với giá trị trên bảng kê ạ.",
        ))
    if r["unused"] > 0:
        out.append((
            "Khi còn phần dư không cấn trừ được",
            f"Dạ, còn {vnd(r['unused'])} giá trị hàng cũ chưa cấn trừ được vì nhóm hàng mới chưa nằm trong phạm vi cho phép "
            "hoặc đã cấn trừ hết hóa đơn. Phần này em xử lý theo quy định của nhóm hàng và sẽ giải thích rõ cho mình ạ.",
        ))
        out.append((
            "Gợi ý để khách cấn trừ được nhiều hơn",
            "Dạ, nếu anh/chị chọn thêm hoặc đổi sang sản phẩm thuộc nhóm được cấn trừ, em có thể tính lại để tận dụng "
            "tối đa giá trị hàng cũ ạ.",
        ))
    return out


# =============================================================== GIAO DIỆN
st.markdown(
    """
<style>
.pnj-banner{background:#0b3566;border-radius:12px;padding:22px 28px;margin-bottom:14px}
.pnj-banner h1{color:#ffd966;font-size:1.8rem;margin:0 0 8px 0;padding:0}
.pnj-banner p{color:#ffffff;font-size:.85rem;margin:0}
.big-number{font-size:2.3rem;font-weight:500;line-height:1.2}
</style>
""",
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="pnj-banner"><h1>💎 {POLICY_TITLE}</h1><p>{POLICY_REF}</p></div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 1. TÍNH TOÁN CẤN TRỪ & PHƯƠNG ÁN THANH TOÁN",
    "📖 2. HƯỚNG DẪN QUY TRÌNH THU ĐỔI (DÀNH CHO KHÁCH & NV)",
    "📊 3. MA TRẬN MAPPING & LỘ TRÌNH THANH TOÁN",
    "❓ 4. HỎI ĐÁP & GỢI Ý TRẢ LỜI KHÁCH",
])

# ---- Tab 3 (vẽ trước để tab 1 dùng được cấu hình đã chỉnh)
with tab3:
    st.header("📊 Ma trận mapping & lộ trình thanh toán")
    st.warning("Dữ liệu đang là SỐ LIỆU MẪU. Hãy thay bằng nội dung thật theo quyết định / Phụ lục A2.")

    st.subheader("Lộ trình thanh toán")
    for step in PAYMENT_ROUTE:
        st.markdown(f"- {step}")

    st.subheader("Hệ số cấn trừ & xử lý phần dư theo nhóm hàng cũ")
    ss.groups_df = st.data_editor(
        ss.groups_df,
        key="groups_editor",
        hide_index=True,
        disabled=[GROUP_COL],
        column_config={
            COEF_COL: st.column_config.NumberColumn(COEF_COL, min_value=0, max_value=100, step=1),
        },
    )

    st.subheader("Ma trận mapping: hàng cũ được cấn trừ vào hàng mới nào")
    st.caption("Tích ✅ nếu nhóm hàng cũ (dòng) được cấn trừ vào nhóm hàng mới (cột).")
    ss.matrix_df = st.data_editor(
        ss.matrix_df,
        key="matrix_editor",
        hide_index=True,
        disabled=[MATRIX_KEY],
    )

group_names = ss.groups_df[GROUP_COL].tolist()
options = [PLACEHOLDER] + group_names

# ---- Tab 1
result = {"has_data": False, "old_total": 0.0, "new_total": 0.0, "applied": 0.0,
          "pay_more": 0.0, "haircut": 0.0, "unused": 0.0}

with tab1:
    st.header("📋 Tính Toán Cấn Trừ & Xác Định Phương Án Thanh Toán")
    left, right = st.columns(2, gap="large")

    with left:
        st.subheader("🛍️ 1. Hàng Cũ Thu Đổi / Mua Lại (Bảng kê)")
        old_items = render_rows("old", "BK", options)
        st.button("➕ Thêm món cũ (BK)", on_click=add_row, args=("old",))
        old_total = sum(i["value"] for i in old_items)
        st.markdown("TỔNG GIÁ TRỊ HÀNG CŨ (BK):")
        st.markdown(f'<div class="big-number">{vnd(old_total)}</div>', unsafe_allow_html=True)

    with right:
        st.subheader("🛒 2. Hàng Mới Khách Mua (Hóa đơn)")
        new_items = render_rows("new", "HĐ", options)
        st.button("➕ Thêm món mới (HĐ)", on_click=add_row, args=("new",))
        new_total_all = sum(i["value"] for i in new_items)
        st.markdown("TỔNG GIÁ TRỊ HÀNG MỚI (HĐ):")
        st.markdown(f'<div class="big-number">{vnd(new_total_all)}</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("💳 Kết quả cấn trừ & phương án thanh toán")

    valid_old = [i for i in old_items if i["group"] != PLACEHOLDER and i["value"] > 0]
    valid_new = [i for i in new_items if i["group"] != PLACEHOLDER and i["value"] > 0]

    skipped = [i["label"] for i in old_items + new_items
               if (i["group"] == PLACEHOLDER) != (i["value"] == 0)]
    if skipped:
        st.warning("Các món chưa nhập đủ nhóm hàng và giá trị sẽ chưa được tính: " + ", ".join(skipped))

    if not valid_old and not valid_new:
        st.info("Chọn nhóm hàng và nhập giá trị ở hai bảng trên để xem kết quả.")
    elif not valid_new:
        st.info("Chưa có hàng mới (HĐ). Nhập hàng mới khách muốn mua để tính cấn trừ.")
    elif not valid_old:
        st.info("Chưa có hàng cũ (BK) – khách thanh toán toàn bộ hóa đơn mới.")
        result.update(has_data=True, new_total=sum(i["value"] for i in valid_new),
                      pay_more=sum(i["value"] for i in valid_new))
    else:
        calc = allocate(valid_old, valid_new, ss.groups_df, ss.matrix_df)
        result.update(has_data=True, old_total=sum(i["value"] for i in valid_old), **{
            k: calc[k] for k in ("new_total", "applied", "pay_more", "haircut", "unused")})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng hàng cũ (BK)", vnd(result["old_total"]))
        m2.metric("Tổng hàng mới (HĐ)", vnd(result["new_total"]))
        m3.metric("Giá trị cấn trừ áp dụng", vnd(result["applied"]))
        m4.metric("Khách thanh toán thêm", vnd(max(result["pay_more"], 0)))

        if result["pay_more"] > 0:
            st.info(f"**Phương án thanh toán:** cấn trừ {vnd(result['applied'])}, khách thanh toán thêm "
                    f"**{vnd(result['pay_more'])}** cho hóa đơn mới.")
        else:
            st.success("**Phương án thanh toán:** giá trị hàng cũ cấn trừ đủ hóa đơn mới, khách không phải thanh toán thêm.")

        if result["unused"] > 0:
            st.warning(f"Còn **{vnd(result['unused'])}** giá trị hàng cũ chưa cấn trừ được. "
                       "Xử lý theo cột 'Xử lý phần dư' bên dưới.")

        st.markdown("**Chi tiết theo từng món cũ**")
        old_df = pd.DataFrame(calc["old_rows"])
        for c in ("Giá trị bảng kê", "Giảm do hệ số", "Phần dư không cấn trừ được"):
            old_df[c] = old_df[c].map(vnd)
        st.dataframe(old_df, hide_index=True)

        if calc["alloc_rows"]:
            st.markdown("**Mapping cấn trừ**")
            alloc_df = pd.DataFrame(calc["alloc_rows"])
            alloc_df["Số tiền cấn trừ"] = alloc_df["Số tiền cấn trừ"].map(vnd)
            st.dataframe(alloc_df, hide_index=True)
        else:
            st.error("Không có món cũ nào được cấn trừ vào hàng mới theo ma trận mapping hiện tại.")

# ---- Tab 2
with tab2:
    st.header("📖 Hướng dẫn quy trình thu đổi")
    st.caption("Nội dung mẫu – cập nhật theo quyết định áp dụng.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.subheader("👤 Dành cho khách hàng")
        for n, s in enumerate(PROCESS_CUSTOMER, start=1):
            st.markdown(f"**{n}.** {s}")
    with c2:
        st.subheader("🧑‍💼 Dành cho nhân viên")
        for n, s in enumerate(PROCESS_STAFF, start=1):
            st.markdown(f"**{n}.** {s}")

# ---- Tab 4
with tab4:
    st.header("❓ Hỏi đáp & gợi ý trả lời khách")

    st.subheader("Gợi ý theo kết quả đang tính ở tab 1")
    for title, text in build_suggestions(result):
        with st.expander(f"💬 {title}"):
            st.code(text, language=None)

    st.subheader("Câu hỏi thường gặp")
    st.caption("Nội dung mẫu – cập nhật theo quy định hiện hành.")
    q = st.text_input("🔎 Tìm câu hỏi", placeholder="Nhập từ khóa, ví dụ: hệ số, giấy tờ, phần dư...")
    shown = [(a, b) for a, b in FAQS if q.strip().lower() in (a + " " + b).lower()]
    if not shown:
        st.info("Không tìm thấy câu hỏi phù hợp.")
    for a, b in shown:
        with st.expander(a):
            st.write(b)