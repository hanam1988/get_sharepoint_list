"""PNJ Trade-in Checker – app Streamlit tra cứu và tính cấn trừ thu đổi.

Căn cứ: PL A2 (hiệu lực 30/09/2026) và TB 442-2026 (28/09/2026).
Chạy: streamlit run app.py
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yaml

from tradein import matrix
from tradein.calc import Case, NewItem, OldItem, Prices, evaluate
from tradein.kc import CLARITIES, SHAPES, TS_PREMIUM, pick_kcr, pick_ts_kc
from tradein.rules import DATA_DIR, describe_rule, fmt_token, load_rules, resolve, rules_meta, rules_of_group
from tradein.scripts import suggest_replies, vnd

st.set_page_config(page_title="Tra cứu thu đổi PNJ", page_icon="💍", layout="wide")

GOLD_AGES = ["99.99", "99.9", "99", "91.6", "75", "68", "61", "58.3", "41.6"]
NL_TOKENS = {"NL", "NL_THU"}


def dec(x) -> Decimal:
    return Decimal(str(x))


@st.cache_data
def load_faq() -> dict:
    return yaml.safe_load((DATA_DIR / "faq.yaml").read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------
# Sidebar: bối cảnh giao dịch và giá nhập tay
# ----------------------------------------------------------------------------
def sidebar() -> tuple[date, object, bool, Prices, dict]:
    st.sidebar.header("Bối cảnh giao dịch")
    store = st.sidebar.radio("Cửa hàng đang làm giao dịch", ["Cửa hàng HUB", "Cửa hàng thường (không phải HUB)"], key="store")
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    txn_date = st.sidebar.date_input("Ngày giao dịch (T)", value=now.date(), format="DD/MM/YYYY", key="txn_date")
    txn_time = st.sidebar.time_input("Giờ giao dịch", value=now.time().replace(second=0, microsecond=0), key="txn_time")

    st.sidebar.subheader("Điều kiện giao dịch")
    cond = {
        "same_customer": st.sidebar.checkbox("Mã khách hàng trên Bảng kê trùng mã trên HĐ mới", value=True, key="same_cust"),
        "intact": st.sidebar.checkbox("Sản phẩm nguyên hiện trạng", value=True, key="intact"),
        "papers": st.sidebar.checkbox("Khách có đủ chứng từ (HĐ PNJ, chính sách bán hàng, giấy giám định nếu có)", value=True, key="papers"),
    }

    st.sidebar.subheader("Giá nguyên liệu (nhập tay)")
    st.sidebar.caption("App không kết nối bảng giá điện tử. Nhập giá niêm yết tại thời điểm thu đổi (đ/chỉ). Giá bằng 0 nghĩa là chưa nhập.")
    table = pd.DataFrame({"Tuổi vàng (%)": GOLD_AGES, "Mua vào": [0] * len(GOLD_AGES), "Bán ra": [0] * len(GOLD_AGES)})
    edited = st.sidebar.data_editor(
        table, hide_index=True, disabled=["Tuổi vàng (%)"], key="gold_prices", use_container_width=True,
        column_config={
            "Mua vào": st.column_config.NumberColumn("Mua vào (đ/chỉ)", min_value=0, step=10_000, format="%d"),
            "Bán ra": st.column_config.NumberColumn("Bán ra (đ/chỉ)", min_value=0, step=10_000, format="%d"),
        },
    )
    platin = st.sidebar.number_input("Đơn giá Platin chuẩn – quy 10 (đ/chỉ)", min_value=0, value=0, step=10_000, format="%d", key="platin")
    gold = {str(r["Tuổi vàng (%)"]): (dec(r["Mua vào"]), dec(r["Bán ra"])) for _, r in edited.iterrows()}
    prices = Prices(gold=gold, platin_std=dec(platin))
    return txn_date, txn_time, store.startswith("Cửa hàng HUB"), prices, cond


# ----------------------------------------------------------------------------
# Danh sách dòng hàng: bố cục 2 cột, mỗi dòng gọn (nhóm hàng | giá trị | chi tiết | xóa)
# ----------------------------------------------------------------------------
OLD_LIMIT, NEW_LIMIT = 6, 4
OLD_GROUPS = list(range(1, 14))
NEW_GROUPS = list(range(1, 11))


def vnd_big(x: Decimal | int) -> str:
    return f"{Decimal(x):,.0f}".replace(",", ".") + " VNĐ"


def init_rows() -> None:
    ss = st.session_state
    ss.setdefault("old_ids", [0])
    ss.setdefault("old_next", 1)
    ss.setdefault("new_ids", [0])
    ss.setdefault("new_next", 1)


def add_row(kind: str, limit: int) -> None:
    ss = st.session_state
    if len(ss[f"{kind}_ids"]) < limit:
        ss[f"{kind}_ids"].append(ss[f"{kind}_next"])
        ss[f"{kind}_next"] += 1


def remove_row(kind: str, rid: int) -> None:
    ids = st.session_state[f"{kind}_ids"]
    if rid in ids:
        ids.remove(rid)


def old_details(rid: int, group: int, inv_value: int, txn_date: date) -> OldItem | None:
    """Phần chi tiết của một món hàng cũ (hiển thị trong popover)."""
    rules = load_rules()
    name = st.text_input("Tên hoặc mã sản phẩm (tùy chọn)", key=f"o{rid}_name")

    candidates: tuple[str, ...] = ()
    kcr_ids: tuple[str, ...] = ()
    use_stone = False
    if group in (2, 5):
        options = ["Kim cương – xác định theo đặc điểm đá", "Dòng hàng khác – chọn từ danh sách"]
        use_stone = st.radio("Cách chọn dòng hàng", options, key=f"o{rid}_how") == options[0]

    if use_stone:
        c1, c2, c3 = st.columns(3)
        shape = c1.selectbox("Hình dáng / loại đá chính", SHAPES, key=f"o{rid}_shape")
        clarity = c2.selectbox("Độ sạch", CLARITIES, index=2, key=f"o{rid}_clar")
        size = c3.number_input("Cỡ lớn nhất (ly)", min_value=0.0, value=4.5, step=0.1, format="%.2f", key=f"o{rid}_size")
        pick = pick_ts_kc(shape, clarity, size) if group == 2 else pick_kcr(shape, clarity, size)
        if pick is None:
            st.error("PL A2 không có dòng hàng phù hợp với tổ hợp hình dáng/độ sạch này. Chuyển P. Vận hành bán lẻ hoặc P.MH xác định.")
            return None
        candidates = pick.candidates
        if pick.note:
            (st.warning if pick.boundary else st.info)(pick.note)
        if "G2-KC-D" in candidates:
            kp = pick_kcr("Tròn (KC trắng)", clarity, size)
            kcr_ids = kp.candidates if kp else ()
    else:
        group_rules = rules_of_group(group)
        rid_rule = st.selectbox("Dòng hàng", [r.id for r in group_rules], format_func=lambda i: rules[i].label, key=f"o{rid}_rule")
        candidates = (rid_rule,)

    inv_date = st.date_input("Ngày xuất hóa đơn", value=txn_date - timedelta(days=365), max_value=txn_date, format="DD/MM/YYYY", key=f"o{rid}_date")
    item = OldItem(rule_ids=candidates, inv_date=inv_date, inv_value=dec(inv_value), name=name)
    item.kcr_rule_ids = kcr_ids

    resolved = [(rules[c], resolve(rules[c], inv_date, txn_date)) for c in candidates]
    needs_nl = any(r.kind == "weight_split" or {res.thu, res.doi} & NL_TOKENS or (res.alt and {res.alt["thu"], res.alt["doi"]} & NL_TOKENS) for r, res in resolved)
    needs_commit = any("CAM_KET_HD" in (res.thu, res.doi) for _, res in resolved)

    for r, res in resolved:
        st.caption(f"**{r.label}** – Thu: {fmt_token(res.thu)} · Đổi: {fmt_token(res.doi)} · Căn cứ: {r.source}")
        for note in res.notes:
            st.caption(f"• {note}")

    if any(r.kind == "split_shell_stone" for r, _ in resolved):
        c1, c2 = st.columns(2)
        item.shell_value = dec(c1.number_input("Giá trị vỏ trên HĐ (đ)", min_value=0, value=0, step=100_000, format="%d", key=f"o{rid}_shell"))
        item.kcr_stone_value = dec(c2.number_input("Giá trị viên đá chính trên HĐ (đ)", min_value=0, value=0, step=100_000, format="%d", key=f"o{rid}_kstone"))
    if needs_commit:
        pct = st.number_input("Tỷ lệ cam kết ghi trên HĐ / chính sách trích lục (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key=f"o{rid}_commit")
        item.cam_ket_ratio = dec(pct) / 100 if pct > 0 else None
    alt = next((res.alt for _, res in resolved if res.alt), None)
    if alt:
        item.use_alt = st.checkbox(f"Khách chọn: {alt['label']}", key=f"o{rid}_alt")
    if any(r.combo_doi is not None for r, _ in resolved):
        item.combo = st.checkbox("Đổi sang Combo mới (TS vỏ + KCR) có tổng giá trị ≥ hàng cũ", key=f"o{rid}_combo")
    if needs_nl:
        st.markdown("**Tính theo giá nguyên liệu**")
        c1, c2, c3 = st.columns(3)
        item.material = c1.radio("Chất liệu", ["Vàng", "Platin"], key=f"o{rid}_mat", horizontal=True)
        if item.material == "Vàng":
            item.tuoi = c2.selectbox("Tuổi vàng (%)", GOLD_AGES, key=f"o{rid}_tuoi")
        else:
            item.tuoi = str(c2.number_input("Tuổi Platin (%)", min_value=0.0, max_value=100.0, value=95.0, step=0.5, key=f"o{rid}_ptuoi"))
        item.tl_hd = dec(c3.number_input("TL vàng/Platin trên HĐ (chỉ)", min_value=0.0, value=0.0, step=0.001, format="%.3f", key=f"o{rid}_tlhd"))
        c4, c5 = st.columns(2)
        actual = c4.number_input("TL thực tế (chỉ) – 0 nếu chưa cân", min_value=0.0, value=0.0, step=0.001, format="%.3f", key=f"o{rid}_tlreal")
        item.tl_thuc_te = dec(actual) if actual > 0 else None
        item.stone_value = dec(c5.number_input("Giá trị đá/ngọc trai (đ)", min_value=0, value=0, step=100_000, format="%d", key=f"o{rid}_stone", help="P.MH định giá hoặc PL A8"))
    return item


def old_row(pos: int, rid: int, txn_date: date) -> tuple[OldItem | None, bool]:
    """Một dòng hàng cũ. Trả về (món hàng hoặc None, đã chọn nhóm hàng)."""
    c1, c2, c3, c4 = st.columns([4.2, 3, 1, 1.6], vertical_alignment="bottom")
    group = c1.selectbox(f"Món BK{pos}:", OLD_GROUPS, index=None, placeholder="-- Chọn nhóm hàng --", format_func=matrix.group_label, key=f"o{rid}_group")
    inv_value = c2.number_input(f"Giá trị BK{pos} (VNĐ):", min_value=0, value=0, step=100_000, format="%d", key=f"o{rid}_inv")
    pop = c3.popover("⚙️", help="Chi tiết: dòng hàng, ngày hóa đơn, giá nguyên liệu", use_container_width=True)
    c4.button("🗑️ Xóa", key=f"o{rid}_del", on_click=remove_row, args=("old", rid), use_container_width=True)
    item = None
    with pop:
        if group is None:
            st.caption("Chọn nhóm hàng trước.")
        else:
            item = old_details(rid, group, inv_value, txn_date)
    return item, group is not None


def new_row(pos: int, rid: int) -> NewItem | None:
    c1, c2, c3 = st.columns([5, 3, 1.6], vertical_alignment="bottom")
    group = c1.selectbox(f"Món HĐ{pos}:", NEW_GROUPS, index=None, placeholder="-- Chọn nhóm hàng --", format_func=matrix.group_label, key=f"n{rid}_group")
    value = c2.number_input(f"Giá trị HĐ{pos} (VNĐ):", min_value=0, value=0, step=100_000, format="%d", key=f"n{rid}_value")
    c3.button("🗑️ Xóa", key=f"n{rid}_del", on_click=remove_row, args=("new", rid), use_container_width=True)
    tlv = None
    if group == 4:
        t = st.number_input(f"TLV hàng mới HĐ{pos} (chỉ)", min_value=0.0, value=0.0, step=0.001, format="%.3f", key=f"n{rid}_tlv", help="Dùng khi đổi cùng nhóm tuổi vàng. Để 0 nếu chưa biết (app coi như TLV mới ≥ TLV cũ).")
        tlv = dec(t) if t > 0 else None
    if group is None or value <= 0:
        return None
    return NewItem(group, dec(value), tlv)


# ----------------------------------------------------------------------------
# Hiển thị kết quả
# ----------------------------------------------------------------------------
OPTION_TITLES = {
    "PA1": "Phương án 1 – chuyển đổi toàn bộ sang sản phẩm mới",
    "PA2": "Phương án 2 – chuyển đổi một phần và nhận tiền phần còn lại",
    "PA3": "Phương án 3 – mua lại hoàn toàn",
}


def render_result(result, case: Case) -> None:
    st.subheader("Kết quả")
    rows = []
    for l in result.lines:
        rows.append({
            "Món": l.name,
            "Dòng hàng": l.label,
            "Áp dụng": l.mode,
            "Cách tính": l.method,
            "Giá trị HĐ": vnd(l.inv_value),
            "Giá trị thu đổi": vnd(l.value),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    for l in result.lines:
        for note in l.notes:
            st.caption(f"• {l.name}: {note}")
        if l.boundary_alt:
            st.caption(f"• {l.name}: dòng còn lại ở biên ({l.boundary_alt[0]}) cho giá trị {vnd(l.boundary_alt[1])}.")
    for w in result.warnings:
        st.warning(w)
    if result.incomplete:
        return

    st.info(f"**Tỷ lệ áp dụng:** {'Đổi' if result.doi_applies else 'Thu'}. {result.doi_reason}")
    m = st.columns(4)
    m[0].metric("Tổng giá trị theo HĐ cũ", vnd(result.total_inv))
    m[1].metric("Giá trị thu đổi (cấn trừ)", vnd(result.total_value))
    m[2].metric("Khách thanh toán thêm", vnd(result.customer_pays))
    m[3].metric("PNJ chi trả cho khách", vnd(result.payout_total))

    st.success(f"**{OPTION_TITLES[result.option]}.** {result.option_reason}")

    if result.payout_total > 0:
        st.markdown("**Nơi thực hiện và khung giờ**")
        if result.hub_ok:
            st.write("✔ Thực hiện tại HUB.")
        else:
            st.error("✘ Giao dịch có chi tiền cho khách phải làm tại HUB; cửa hàng này không phải HUB.")
        if result.window_ok is True:
            st.write("✔ Trong khung giờ tiếp nhận Mua Lại (15h00–17h00).")
        elif result.window_ok is False:
            st.error("✘ Ngoài khung giờ tiếp nhận Mua Lại (15h00–17h00).")

        st.markdown("**Lộ trình chi trả cho khách** (mốc T là ngày giao dịch)")
        for pg in result.payouts:
            st.caption(f"Nhóm {pg.group} – tổng {vnd(pg.amount)}")
            st.dataframe(
                pd.DataFrame([{"Mốc": r.offset, "Tỷ lệ": f"{r.pct}%", "Số tiền": vnd(r.amount)} for r in pg.rows]),
                hide_index=True, use_container_width=True,
            )

    st.markdown("**Chứng từ cần có**")
    for doc in result.documents:
        st.checkbox(doc, key=f"doc_{doc[:30]}")

    st.markdown("**Gợi ý câu trả lời cho khách**")
    for title, text in suggest_replies(result):
        with st.expander(title, expanded=False):
            st.code(text, language=None, wrap_lines=True)


def tab_calc() -> None:
    init_rows()
    txn_date, txn_time, is_hub, prices, cond = sidebar()
    docs = matrix.documents()

    left, right = st.columns(2, gap="large")
    old_items: list[OldItem | None] = []
    with left:
        st.markdown("### 🛍️ 1. Hàng cũ thu đổi / mua lại (Bảng kê)")
        for pos, rid in enumerate(st.session_state.old_ids, start=1):
            item, picked = old_row(pos, rid, txn_date)
            old_items.append(item if picked else None)
        st.button("➕ Thêm món cũ (BK)", key="old_add", on_click=add_row, args=("old", OLD_LIMIT), disabled=len(st.session_state.old_ids) >= OLD_LIMIT)
        total_old = sum((dec(st.session_state.get(f"o{rid}_inv", 0)) for rid in st.session_state.old_ids), Decimal(0))
        st.caption("TỔNG GIÁ TRỊ HÀNG CŨ (BK):")
        st.markdown(f"## {vnd_big(total_old)}")
    new_items: list[NewItem] = []
    with right:
        st.markdown("### 🛒 2. Hàng mới khách mua (Hóa đơn)")
        for pos, rid in enumerate(st.session_state.new_ids, start=1):
            n = new_row(pos, rid)
            if n:
                new_items.append(n)
        st.button("➕ Thêm món mới (HĐ)", key="new_add", on_click=add_row, args=("new", NEW_LIMIT), disabled=len(st.session_state.new_ids) >= NEW_LIMIT)
        total_new = sum((dec(st.session_state.get(f"n{rid}_value", 0)) for rid in st.session_state.new_ids), Decimal(0))
        st.caption("TỔNG GIÁ TRỊ HÀNG MỚI (HĐ):")
        st.markdown(f"## {vnd_big(total_new)}")
    st.caption("Không có món hàng mới (hoặc để trống) nghĩa là khách chỉ bán lại.")

    if not cond["intact"]:
        st.error("Sản phẩm không nguyên hiện trạng: A2 mục 3 có công thức riêng theo từng trường hợp (mất đá, mất chi tiết, hao hụt, biến dạng, thiếu dấu mộc). App chưa tự tính; xem tab Quy trình hoặc chuyển P.TL&ĐBCL. Kết quả bên dưới chỉ để tham khảo cho phần nguyên hiện trạng.")
    if not cond["papers"]:
        st.warning("Thiếu chứng từ: nếu nhận diện được là hàng PNJ thì xử lý theo từng trường hợp; một số dòng hàng ghi rõ không thu mua khi thiếu chứng từ.")

    st.divider()
    if not old_items:
        st.info("Chưa có món hàng cũ. Bấm “Thêm món cũ (BK)” để bắt đầu.")
        return
    if any(i is None for i in old_items):
        st.info("Chọn nhóm hàng cho từng món hàng cũ (và hoàn tất chi tiết ở nút ⚙️ nếu cần) để xem kết quả.")
        return
    if any(i.inv_value <= 0 for i in old_items):
        st.info("Nhập giá trị theo hóa đơn của từng món hàng cũ để xem kết quả.")
        return
    case = Case(old=old_items, new=new_items, txn_date=txn_date, same_customer=cond["same_customer"], prices=prices, is_hub=is_hub, txn_time=txn_time)
    try:
        result = evaluate(case)
    except ValueError as exc:
        st.error(f"Không tính được: {exc}")
        return
    render_result(result, case)
    st.caption(f"Căn cứ: {docs['a2']} (hiệu lực {docs['a2_effective']}) và {docs['tb']} ({docs['tb_date']}). Công cụ tham khảo; trường hợp vướng mắc liên hệ P. Vận hành bán lẻ.")


def tab_guide() -> None:
    st.markdown("Tóm tắt quy trình theo PL A2 và TB 442-2026. Văn bản gốc là căn cứ cuối cùng.")
    for i, step in enumerate(load_faq()["guide"]):
        with st.expander(step["title"], expanded=i == 0):
            st.markdown(step["body"])


def tab_matrix() -> None:
    groups = matrix.groups()
    conv = matrix.conversion()
    st.markdown("#### Ma trận chuyển đổi thanh toán")
    st.caption("Hàng = nhóm hàng cũ; cột = nhóm hàng mới được phép chuyển đổi. Đã đối chiếu khớp giữa PL A2, Excel mapping và TB 442.")
    cols = list(range(1, 11))
    df = pd.DataFrame({f"Mới {c}": ["✔" if c in conv[g] else "" for g in range(1, 14)] for c in cols}, index=[f"Cũ {g}" for g in range(1, 14)])
    st.dataframe(df, use_container_width=True)

    st.markdown("#### Nhóm hàng và lộ trình thanh toán")
    sched = {k: v for k, v in matrix._raw()["schedules"].items()}
    rows = []
    for g, info in groups.items():
        s = sched[info["schedule"]]
        plan = "; ".join(f"{r['pct']}% {r['offset']}" for r in s["rows"])
        rows.append({"Nhóm": g, "Mã (ảnh)": info["code"], "Dòng hàng": info["name"], "Thời gian": s["label"], "Lộ trình": plan, "Quota": info["quota"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    legacy = matrix.legacy_t120()
    st.caption(f"Giao dịch T+120 đã xác lập trước đó: nhóm {', '.join(map(str, legacy['paid_in_full']))} được chi trả toàn bộ phần còn lại; nhóm {', '.join(map(str, legacy['keep_schedule']))} giữ nguyên lộ trình đã thỏa thuận.")

    st.markdown("#### Tỷ lệ thu đổi theo dòng hàng")
    group = st.selectbox("Chọn nhóm hàng", list(range(1, 14)), format_func=matrix.group_label, key="view_group")
    for r in rules_of_group(group):
        with st.expander(r.label):
            st.dataframe(pd.DataFrame(describe_rule(r)), hide_index=True, use_container_width=True)
            if r.min_value:
                st.caption(f"Giá trị tối thiểu để thu mua: {vnd(r.min_value)}.")
            for note in r.notes:
                st.caption(f"• {note}")
            st.caption(f"Căn cứ: {r.source}")
    meta = rules_meta()
    st.caption(f"Dữ liệu quy tắc: phiên bản {meta['version']}, hiệu lực từ {meta['effective_from']}.")


def tab_qa() -> None:
    q = st.text_input("Tìm câu hỏi", placeholder="ví dụ: HUB, khung giờ, Phụ lục 01, T+120", key="qa_search")
    items = load_faq()["qa"]
    needle = q.strip().casefold()
    shown = [x for x in items if not needle or needle in x["q"].casefold() or needle in x["a"].casefold()]
    if not shown:
        st.info("Không có mục phù hợp. Liên hệ P. Vận hành bán lẻ (Diệp Nguyễn Yến Phương) để được hỗ trợ.")
    for x in shown:
        with st.expander(x["q"]):
            st.write(x["a"])


def main() -> None:
    docs = matrix.documents()
    st.title("💍 Tra cứu thu đổi PNJ")
    st.info(f"Áp dụng: **TB 442-2026** ngày {docs['tb_date']} (từ {docs['tb_effective']}) và **PL A2** hiệu lực {docs['a2_effective']}. Thông báo có hiệu lực đến khi có thông báo mới.")
    t1, t2, t3, t4 = st.tabs(["🧮 Tính cấn trừ", "📋 Quy trình", "🔀 Ma trận & thanh toán", "💬 Q&A"])
    with t1:
        tab_calc()
    with t2:
        tab_guide()
    with t3:
        tab_matrix()
    with t4:
        tab_qa()


main()
