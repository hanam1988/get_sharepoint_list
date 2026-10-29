"""Tính cấn trừ thu đổi, điều kiện Đổi, phương án 1/2/3 và lộ trình chi trả.

Mọi phép tính tiền dùng Decimal. Tỷ lệ và nhóm hàng lấy từ data/*.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal

from . import matrix
from .rules import REF_TOKENS, Resolved, Rule, fmt_token, load_rules, resolve

ZERO = Decimal("0")
WEIGHT_TOLERANCE = Decimal("0.006")  # chỉ
DONG = Decimal("1")


def money(x: Decimal) -> Decimal:
    return x.quantize(DONG, rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------------
# Dữ liệu vào
# ----------------------------------------------------------------------------
@dataclass
class Prices:
    """Giá nhập tay (đ/chỉ). Không có giá mặc định."""

    gold: dict[str, tuple[Decimal, Decimal]] = field(default_factory=dict)  # tuổi -> (mua vào, bán ra)
    platin_std: Decimal = ZERO  # đơn giá Platin chuẩn (quy 10)


@dataclass
class OldItem:
    rule_ids: tuple[str, ...]  # 1 dòng, hoặc 2 dòng khi đúng giá trị biên
    inv_date: date
    inv_value: Decimal  # tổng giá trị theo HĐ (đ)
    name: str = ""
    # Giá nguyên liệu
    material: str = "Vàng"  # "Vàng" | "Platin"
    tuoi: str = ""  # Vàng: khóa trong Prices.gold; Platin: phần trăm, ví dụ "95"
    tl_hd: Decimal = ZERO  # chỉ
    tl_thuc_te: Decimal | None = None
    stone_value: Decimal = ZERO  # giá trị đá nhập tay (P.MH định giá / PL A8 / giá HĐ)
    # Lựa chọn khác
    cam_ket_ratio: Decimal | None = None  # tỷ lệ theo cam kết trên HĐ (0..1)
    use_alt: bool = False  # chọn phương án "Thu theo giá NL" khi dòng hàng cho khách chọn
    combo: bool = False  # đổi sang combo mới (TS vỏ + KCR)
    # Dòng tách vỏ/viên (TS KC ≥4ly)
    shell_value: Decimal = ZERO
    kcr_stone_value: Decimal = ZERO
    kcr_rule_ids: tuple[str, ...] = ()


@dataclass
class NewItem:
    group: int
    value: Decimal
    tlv: Decimal | None = None  # chỉ; dùng cho nhóm 4 (tuổi vàng)


@dataclass
class Case:
    old: list[OldItem]
    new: list[NewItem]
    txn_date: date
    same_customer: bool = True
    prices: Prices = field(default_factory=Prices)
    is_hub: bool = True
    txn_time: time | None = None


# ----------------------------------------------------------------------------
# Kết quả
# ----------------------------------------------------------------------------
@dataclass
class LineResult:
    name: str
    rule_id: str
    label: str
    group: int
    mode: str  # "Đổi" | "Thu"
    method: str  # mô tả cách tính
    value: Decimal | None  # None = chưa tính được
    inv_value: Decimal
    notes: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    source: str = ""
    boundary_alt: tuple[str, Decimal | None] | None = None


@dataclass
class PayoutRow:
    offset: str
    pct: int
    amount: Decimal


@dataclass
class PayoutGroup:
    group: int
    amount: Decimal
    rows: list[PayoutRow]


@dataclass
class CaseResult:
    lines: list[LineResult]
    eligible: list[bool]
    doi_applies: bool
    doi_reason: str
    option: str  # "PA1" | "PA2" | "PA3" | "" (chưa xác định)
    option_reason: str
    total_inv: Decimal
    total_value: Decimal | None
    new_total: Decimal
    customer_pays: Decimal
    payout_total: Decimal
    payouts: list[PayoutGroup]
    hub_ok: bool
    window_ok: bool | None
    warnings: list[str]
    incomplete: bool
    documents: list[str]


# ----------------------------------------------------------------------------
# Tính từng món
# ----------------------------------------------------------------------------
def effective_weight(tl_hd: Decimal, tl_thuc_te: Decimal | None) -> Decimal:
    """Dung sai ±0,006 chỉ: trong dung sai lấy TL trên HĐ, vượt thì lấy TL thực tế (A2 mục 2.1)."""
    if tl_thuc_te is None:
        return tl_hd
    return tl_hd if abs(tl_thuc_te - tl_hd) <= WEIGHT_TOLERANCE else tl_thuc_te


def _nl_value(item: OldItem, side: str, res: Resolved, prices: Prices, weight: Decimal | None = None, include_stone: bool = True) -> tuple[Decimal | None, list[str], list[str]]:
    """Giá trị theo giá nguyên liệu. side: 'mua_vao' (Thu) hoặc 'ban_ra' (Đổi)."""
    notes: list[str] = []
    missing: list[str] = []
    w = weight if weight is not None else effective_weight(item.tl_hd, item.tl_thuc_te)
    if w <= 0:
        missing.append("trọng lượng")
    price = ZERO
    if item.material == "Platin":
        try:
            tuoi = Decimal(item.tuoi or "0") / 100
        except Exception:  # noqa: BLE001 - dữ liệu nhập tay
            tuoi = ZERO
        price = prices.platin_std * tuoi
        if price <= 0:
            missing.append("đơn giá Platin chuẩn và tuổi Platin")
        notes.append("Platin: TL × đơn giá NL (đơn giá chuẩn × tuổi Platin), cùng giá cho Thu và Đổi.")
    else:
        pair = prices.gold.get(item.tuoi)
        if pair is not None:
            price = pair[0] if side == "mua_vao" else pair[1]
        if price <= 0:
            missing.append(f"giá vàng {'mua vào' if side == 'mua_vao' else 'bán ra'} tuổi {item.tuoi or '?'}")
    if missing:
        return None, notes, missing
    metal = w * price
    stone = ZERO
    if item.stone_value > 0 and include_stone:
        factor = res.stone_factor if res.stone_factor is not None else Decimal("1")
        stone = item.stone_value * factor
        if res.stone_factor is None:
            notes.append("Giá trị đá lấy theo số nhập tay (P.MH định giá / PL A8); app không tự định giá đá.")
        elif res.stone_factor == 0:
            notes.append("Đá/ngọc trai không thu đổi theo quy định.")
        else:
            notes.append(f"Đá tính {fmt_token(res.stone_factor)} giá trị đá.")
    return money(metal + stone), notes, missing


def _value_for(item: OldItem, rule: Rule, res: Resolved, mode: str, prices: Prices, weight_split: tuple[Decimal, Decimal] | None) -> tuple[Decimal | None, str, list[str], list[str]]:
    """Giá trị của một món theo chế độ Thu/Đổi. Trả (value, method, notes, missing)."""
    token = res.doi if mode == "Đổi" else res.thu
    if item.use_alt and res.alt:
        token = res.alt["doi"] if mode == "Đổi" else res.alt["thu"]
    notes: list[str] = list(res.notes)
    if res.alt and item.use_alt:
        notes.append(f"Khách chọn: {res.alt['label']}.")

    if isinstance(token, Decimal):
        if mode == "Đổi" and item.combo and rule.combo_doi is not None:
            token = rule.combo_doi
            notes.append("Áp dụng tỷ lệ đổi Combo mới (TS vỏ + KCR).")
        if rule.min_value is not None and item.inv_value < rule.min_value:
            return ZERO, "Dưới mức tối thiểu: không thu mua", notes + [f"Giá trị HĐ dưới {rule.min_value:,.0f} đ nên không thu mua.".replace(",", ".")], []
        return money(item.inv_value * token), f"{fmt_token(token)} × giá trị HĐ", notes, []

    if token == "KHONG":
        return ZERO, "Không thu mua", notes, []
    if token == "CAM_KET_HD":
        if item.cam_ket_ratio is None:
            return None, "Theo cam kết trên HĐ", notes, ["tỷ lệ cam kết trên HĐ"]
        return money(item.inv_value * item.cam_ket_ratio), f"{fmt_token(item.cam_ket_ratio)} (cam kết trên HĐ) × giá trị HĐ", notes, []
    if token == "CAN_DUYET":
        return None, "Chỉ áp dụng khi được duyệt theo tờ trình", notes, ["quyết định duyệt theo tờ trình"]
    if token in REF_TOKENS:
        return None, f"Tra {REF_TOKENS[token]}", notes, [f"tra {REF_TOKENS[token]}"]

    if token in ("NL", "NL_THU"):
        if token == "NL_THU" or mode == "Thu":
            side, method = "mua_vao", "Thu theo giá nguyên liệu (giá mua vào)"
        else:
            side, method = "ban_ra", "Đổi theo giá nguyên liệu (giá bán ra)"
        if weight_split is not None and rule.kind == "weight_split":
            w_doi, w_thu = weight_split
            v_doi, n1, m1 = _nl_value(item, "ban_ra", res, prices, w_doi) if w_doi > 0 else (ZERO, [], [])
            v_thu, n2, m2 = _nl_value(item, "mua_vao", res, prices, w_thu, include_stone=w_doi <= 0) if w_thu > 0 else (ZERO, [], [])
            missing = m1 + m2
            if missing:
                return None, method, notes + n1 + n2, missing
            note = f"TLV hàng mới thấp hơn TLV cũ: {w_doi} chỉ Đổi NL + {w_thu} chỉ Thu NL."
            return money((v_doi or ZERO) + (v_thu or ZERO)), "Tách TLV: Đổi NL và Thu NL", notes + [note] + n1 + n2, []
        value, n, missing = _nl_value(item, side, res, prices)
        return value, method, notes + n, missing
    raise ValueError(f"Token không hỗ trợ: {token!r}")


def compute_item(item: OldItem, mode: str, txn_date: date, prices: Prices, weight_split: tuple[Decimal, Decimal] | None = None) -> LineResult:
    """Tính một món. Nếu có 2 dòng ứng viên (đúng giá trị biên) thì lấy giá trị thấp hơn."""
    rules = load_rules()
    results: list[LineResult] = []
    for rule_id in item.rule_ids:
        rule = rules[rule_id]
        res = resolve(rule, item.inv_date, txn_date)
        if rule.kind == "split_shell_stone":
            results.append(_compute_split(item, rule, mode, txn_date, prices))
            continue
        value, method, notes, missing = _value_for(item, rule, res, mode, prices, weight_split)
        results.append(
            LineResult(item.name or rule.label, rule.id, rule.label, rule.payment_group, mode, method, value, item.inv_value, notes, missing, rule.source)
        )
    if len(results) == 1:
        return results[0]
    comparable = [r for r in results if r.value is not None]
    if len(comparable) == len(results):
        best = min(results, key=lambda r: r.value)  # type: ignore[arg-type,return-value]
        other = next(r for r in results if r is not best)
        best.boundary_alt = (other.label, other.value)
        best.notes.append("Đúng giá trị biên giữa hai dòng hàng: lấy giá trị thấp hơn (mặc định của app, cần xác nhận với P. Vận hành bán lẻ).")
        return best
    first = results[0]
    first.notes.append("Đúng giá trị biên giữa hai dòng hàng nhưng chưa đủ dữ liệu để so sánh.")
    first.value = None
    first.missing = sorted({m for r in results for m in r.missing})
    return first


def _compute_split(item: OldItem, rule: Rule, mode: str, txn_date: date, prices: Prices) -> LineResult:
    """TS KC ≥4ly: vỏ theo tỷ lệ vỏ, viên theo tỷ lệ KCR (A2: ví dụ KC 4,5ly VVS1 → 93 triệu)."""
    shell_ratio = rule.shell_doi if mode == "Đổi" else rule.shell_thu
    notes = list(rule.notes)
    missing: list[str] = []
    if item.shell_value <= 0 and item.kcr_stone_value <= 0:
        missing.append("giá trị vỏ và giá trị viên trên HĐ")
    if not item.kcr_rule_ids:
        missing.append("dòng KCR của viên đá chính")
    if missing:
        return LineResult(item.name or rule.label, rule.id, rule.label, rule.payment_group, mode, "Tách vỏ và viên", None, item.inv_value, notes, missing, rule.source)
    stone_item = OldItem(rule_ids=item.kcr_rule_ids, inv_date=item.inv_date, inv_value=item.kcr_stone_value, cam_ket_ratio=item.cam_ket_ratio)
    stone_res = compute_item(stone_item, mode, txn_date, prices)
    if stone_res.value is None:
        return LineResult(item.name or rule.label, rule.id, rule.label, rule.payment_group, mode, "Tách vỏ và viên", None, item.inv_value, notes + stone_res.notes, stone_res.missing, rule.source)
    shell_value = money(item.shell_value * shell_ratio)
    total = shell_value + stone_res.value
    method = f"Vỏ {fmt_token(shell_ratio)} × {item.shell_value:,.0f} + viên ({stone_res.method}) × {item.kcr_stone_value:,.0f}".replace(",", ".")
    notes += [f"Viên theo dòng KCR: {stone_res.label}."] + stone_res.notes
    return LineResult(item.name or rule.label, rule.id, rule.label, rule.payment_group, mode, method, total, item.inv_value, notes, [], rule.source)


# ----------------------------------------------------------------------------
# Điều kiện Đổi, phương án, chi trả
# ----------------------------------------------------------------------------
def _item_group(item: OldItem) -> int:
    return load_rules()[item.rule_ids[0]].payment_group


def _allocate(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Chia amount theo tỷ trọng, phần dư dồn vào phần tử cuối để tổng khớp tuyệt đối."""
    total = sum(weights, ZERO)
    if amount <= 0 or total <= 0:
        return [ZERO for _ in weights]
    parts = [money(amount * w / total) for w in weights]
    parts[-1] += amount - sum(parts, ZERO)
    return parts


def payout_schedule(group: int, amount: Decimal) -> PayoutGroup:
    rows_cfg = matrix.schedule_for_group(group)["rows"]
    pcts = [Decimal(r["pct"]) for r in rows_cfg]
    amounts = _allocate(amount, pcts)
    return PayoutGroup(group, amount, [PayoutRow(r["offset"], int(r["pct"]), a) for r, a in zip(rows_cfg, amounts)])


def evaluate(case: Case) -> CaseResult:
    warnings: list[str] = []
    groups_old = [_item_group(i) for i in case.old]
    new_items = [n for n in case.new if n.value > 0]
    new_groups = {n.group for n in new_items}
    new_total = sum((n.value for n in new_items), ZERO)

    # 1) Món nào có thể chuyển đổi (nhóm cũ → ít nhất một nhóm mới được phép)
    eligible = [any(g in matrix.allowed_new_groups(og) for g in new_groups) for og in groups_old]
    usable_new_groups = {g for og, ok in zip(groups_old, eligible) if ok for g in matrix.allowed_new_groups(og)}
    n_elig = sum((n.value for n in new_items if n.group in usable_new_groups), ZERO)
    old_elig_inv = sum((i.inv_value for i, ok in zip(case.old, eligible) if ok), ZERO)

    # 2) Điều kiện được hưởng tỷ lệ Đổi (A2 mục 2.2)
    if not any(eligible):
        doi_applies, reason = False, "Không có hàng mới thuộc nhóm được chuyển đổi nên áp dụng tỷ lệ Thu."
    elif not case.same_customer:
        doi_applies, reason = False, "Mã khách hàng trên Bảng kê và HĐ mới không trùng nên áp dụng tỷ lệ Thu."
    elif n_elig < old_elig_inv:
        doi_applies, reason = False, "Tổng giá trị hàng mới (nhóm được chuyển đổi) nhỏ hơn tổng giá trị hàng cũ theo HĐ nên áp dụng tỷ lệ Thu."
    else:
        doi_applies, reason = True, "Đủ điều kiện hưởng tỷ lệ Đổi."

    # 3) Tách TLV cho nhóm 4 khi đổi cùng nhóm (A2 nhóm 3: TLV mới < TLV cũ)
    tlv_new_g4 = sum((n.tlv or ZERO for n in new_items if n.group == 4), ZERO)
    has_tlv_new = any(n.group == 4 and n.tlv is not None for n in new_items)
    remaining_doi_weight = tlv_new_g4

    lines: list[LineResult] = []
    for item, og, ok in zip(case.old, groups_old, eligible):
        mode = "Đổi" if (ok and doi_applies) else "Thu"
        split = None
        rule0 = load_rules()[item.rule_ids[0]]
        if mode == "Đổi" and rule0.kind == "weight_split" and has_tlv_new:
            old_w = effective_weight(item.tl_hd, item.tl_thuc_te)
            w_doi = min(old_w, remaining_doi_weight)
            remaining_doi_weight -= w_doi
            if w_doi < old_w:
                split = (w_doi, old_w - w_doi)
        lines.append(compute_item(item, mode, case.txn_date, case.prices, split))

    incomplete = any(l.value is None for l in lines)
    total_inv = sum((i.inv_value for i in case.old), ZERO)
    docs = ["Bảng kê thu mua hàng hóa mua vào không có hóa đơn (Mẫu 02/TNDN)"]
    if incomplete:
        reasons = sorted({m for l in lines for m in l.missing})
        warnings.append("Chưa đủ dữ liệu để chốt kết quả: thiếu " + "; ".join(reasons) + ".")
        return CaseResult(lines, eligible, doi_applies, reason, "", "", total_inv, None, new_total, ZERO, ZERO, [], True, None, warnings, True, docs)

    values = [l.value or ZERO for l in lines]
    total_value = sum(values, ZERO)
    v_elig = sum((v for v, ok in zip(values, eligible) if ok), ZERO)
    v_non = total_value - v_elig

    # 4) Phương án
    if not any(eligible):
        option, why = "PA3", "Không chuyển đổi được sang hàng mới đã chọn nên chỉ còn phương án 3 (mua lại hoàn toàn)."
        payout_by_item = values[:]
        customer_pays = new_total
    elif doi_applies or n_elig >= v_elig:
        option, why = "PA1", "Hàng mới có giá trị bằng hoặc cao hơn giá trị mua lại: chuyển đổi toàn bộ."
        payout_by_item = [ZERO if ok else v for v, ok in zip(values, eligible)]
        customer_pays = max(ZERO, new_total - v_elig)
    else:
        option, why = "PA2", "Hàng mới có giá trị thấp hơn giá trị mua lại: chuyển đổi một phần, phần còn lại chi trả bằng tiền theo lộ trình."
        extra = v_elig - n_elig
        elig_shares = _allocate(extra, [v for v, ok in zip(values, eligible) if ok])
        it = iter(elig_shares)
        payout_by_item = [next(it) if ok else v for v, ok in zip(values, eligible)]
        customer_pays = max(ZERO, new_total - n_elig)
    if option != "PA3" and v_non > 0:
        why += " Phần hàng cũ không chuyển đổi được (nếu có) vẫn là mua lại và chi trả bằng tiền."
    payout_total = sum(payout_by_item, ZERO)

    # 5) Lộ trình chi trả theo nhóm hàng cũ
    per_group: dict[int, Decimal] = {}
    for og, amount in zip(groups_old, payout_by_item):
        if amount > 0:
            per_group[og] = per_group.get(og, ZERO) + amount
    payouts = [payout_schedule(g, a) for g, a in sorted(per_group.items())]

    # 6) HUB, khung giờ, chứng từ
    hub_ok = case.is_hub or payout_total <= 0
    window_ok: bool | None = None
    if payout_total > 0:
        if not case.is_hub:
            warnings.append("Giao dịch có chi tiền cho khách là Mua Lại và bắt buộc thực hiện tại HUB. Cửa hàng thường chỉ nhận giao dịch chuyển đổi sang hàng mới có giá trị ≥ giá trị mua lại.")
        if case.txn_time is not None:
            window_ok = matrix.in_buyback_window(case.txn_time)
            if not window_ok:
                start, stop = matrix.buyback_window()
                warnings.append(f"Ngoài khung giờ tiếp nhận Mua Lại ({start:%H:%M}–{stop:%H:%M}); từ {stop:%H:%M} ngừng phát số.")
        warnings.append("Kiểm tra hạn mức tiền mặt theo ngày và dòng hàng với KTT chi nhánh trước khi tiếp nhận (app không biết hạn mức còn lại).")
    if option == "PA2":
        docs.append("Phụ lục 01 Thỏa thuận thu đổi sản phẩm: in 2 bản, khách giữ 1 bản, cửa hàng lưu 1 bản")
    docs.append("Cửa hàng lưu bản cứng có mộc đỏ của 'Thông báo về hồ sơ giao dịch mua hàng giữa PNJ và khách hàng'")

    return CaseResult(lines, eligible, doi_applies, reason, option, why, total_inv, total_value, new_total, customer_pays, payout_total, payouts, hub_ok, window_ok, warnings, False, docs)
