from datetime import date, time
from decimal import Decimal as D

from tradein.calc import Case, NewItem, OldItem, Prices, effective_weight, evaluate, payout_schedule
from tradein.scripts import suggest_replies

TXN = date(2026, 10, 29)
GOLD = Prices(gold={"99.99": (D(8_000_000), D(8_500_000)), "99": (D(7_900_000), D(8_400_000))}, platin_std=D(7_000_000))


def kc_example(new_value, group=2):
    """Ví dụ minh họa trong A2: HĐ 100tr (vỏ 20tr, viên 80tr, KC 4,5ly VVS1)."""
    item = OldItem(rule_ids=("G2-KC-D",), inv_date=date(2025, 12, 1), inv_value=D(100_000_000),
                   shell_value=D(20_000_000), kcr_stone_value=D(80_000_000), kcr_rule_ids=("G5-KCR-LT5",))
    return Case(old=[item], new=[NewItem(group, D(new_value))], txn_date=TXN)


def test_golden_a2_kc_example_doi_93_million():
    r = evaluate(kc_example(105_000_000))
    assert r.doi_applies and r.option == "PA1"
    assert r.total_value == D(93_000_000)  # vỏ 20tr×85% = 17tr + viên 80tr×95% = 76tr
    assert r.customer_pays == D(12_000_000)
    assert r.payout_total == 0


def test_same_example_falls_back_to_thu_when_new_value_too_low():
    r = evaluate(kc_example(50_000_000))
    assert not r.doi_applies and r.option == "PA2"
    assert r.total_value == D(20_000_000) * D("0.8") + D(80_000_000) * D("0.93")  # 16tr + 74,4tr
    assert r.payout_total == r.total_value - D(50_000_000)
    assert r.customer_pays == 0
    assert "Phụ lục 01" in " ".join(r.documents)


def test_sell_back_only_is_pa3_with_t120_schedule():
    r = evaluate(Case(old=kc_example(0).old, new=[], txn_date=TXN))
    assert r.option == "PA3"
    assert r.payout_total == r.total_value
    sch = r.payouts[0]
    assert sch.group == 2 and [row.offset for row in sch.rows] == ["T/T+1", "T+30", "T+60", "T+90", "T+120"]
    assert sum(row.amount for row in sch.rows) == sch.amount


def test_new_group_not_convertible_forces_pa3():
    # KCR (nhóm 5) chỉ đổi được sang nhóm 2 và 5; mua hàng nhóm 10 thì không chuyển đổi được
    old = OldItem(rule_ids=("G5-KCR-6-86",), inv_date=date(2025, 6, 1), inv_value=D(50_000_000))
    r = evaluate(Case(old=[old], new=[NewItem(10, D(60_000_000))], txn_date=TXN))
    assert r.option == "PA3" and not r.doi_applies
    assert r.total_value == D(47_500_000)  # Thu 95%
    assert r.customer_pays == D(60_000_000)


def test_different_customer_code_uses_thu():
    case = kc_example(105_000_000)
    case.same_customer = False
    r = evaluate(case)
    assert not r.doi_applies
    assert r.total_value == D(16_000_000) + D(74_400_000)


def test_non_hub_with_payout_warns_and_window_check():
    case = kc_example(50_000_000)
    case.is_hub, case.txn_time = False, time(10, 0)
    r = evaluate(case)
    assert not r.hub_ok and r.window_ok is False
    text = " ".join(r.warnings)
    assert "HUB" in text and "15:00" in text


def test_hub_inside_window_has_no_window_warning():
    case = kc_example(50_000_000)
    case.is_hub, case.txn_time = True, time(15, 30)
    r = evaluate(case)
    assert r.hub_ok and r.window_ok is True
    assert not any("khung giờ" in w for w in r.warnings)


def test_non_hub_pa1_has_no_hub_requirement():
    case = kc_example(105_000_000)
    case.is_hub = False
    r = evaluate(case)
    assert r.hub_ok and r.payout_total == 0


def test_weight_tolerance():
    assert effective_weight(D("1.000"), D("1.006")) == D("1.000")
    assert effective_weight(D("1.000"), D("0.994")) == D("1.000")
    assert effective_weight(D("1.000"), D("1.007")) == D("1.007")
    assert effective_weight(D("1.000"), None) == D("1.000")


def test_golden_platin_prices():
    for tuoi, expected in (("90", D(6_300_000)), ("95", D(6_650_000))):
        item = OldItem(rule_ids=("G3-KGD-DC",), inv_date=date(2026, 3, 1), inv_value=D(10_000_000),
                       material="Platin", tuoi=tuoi, tl_hd=D(1))
        r = evaluate(Case(old=[item], new=[], txn_date=TXN, prices=GOLD))
        assert r.total_value == expected


def test_nl_missing_price_blocks_result():
    item = OldItem(rule_ids=("G3-KGD-DC",), inv_date=date(2026, 3, 1), inv_value=D(10_000_000), tuoi="99", tl_hd=D(1))
    r = evaluate(Case(old=[item], new=[], txn_date=TXN, prices=Prices()))
    assert r.incomplete and r.option == "" and r.total_value is None
    assert "giá vàng" in " ".join(r.warnings)


def test_golden_group4_split_weight_same_group():
    """A2 nhóm 3: TLV cũ 10 chỉ, TLV mới 9 chỉ → 9 chỉ Đổi NL + 1 chỉ Thu NL (HĐ trước 05/01/2026)."""
    old = OldItem(rule_ids=("G4-TUOIVANG",), inv_date=date(2025, 6, 1), inv_value=D(80_000_000), tuoi="99.99", tl_hd=D(10))
    # hàng mới cùng nhóm, giá trị ≥ HĐ cũ nhưng TLV 9 chỉ
    r = evaluate(Case(old=[old], new=[NewItem(4, D(90_000_000), tlv=D(9))], txn_date=TXN, prices=GOLD))
    assert r.doi_applies
    assert r.total_value == D(9) * D(8_500_000) + D(1) * D(8_000_000)  # 84,5tr
    r2 = evaluate(Case(old=[old], new=[NewItem(4, D(90_000_000), tlv=D(12))], txn_date=TXN, prices=GOLD))
    assert r2.total_value == D(10) * D(8_500_000)  # TLV mới ≥ cũ: toàn bộ Đổi NL


def test_gold_after_5_jan_2026_always_buy_in_price():
    old = OldItem(rule_ids=("G4-TUOIVANG",), inv_date=date(2026, 2, 1), inv_value=D(80_000_000), tuoi="99.99", tl_hd=D(10))
    r = evaluate(Case(old=[old], new=[NewItem(4, D(90_000_000), tlv=D(10))], txn_date=TXN, prices=GOLD))
    assert r.total_value == D(10) * D(8_000_000)


def test_stone_factor_half_for_gold_with_stone_after_jan_2026():
    old = OldItem(rule_ids=("G4-TUOIVANG",), inv_date=date(2026, 2, 1), inv_value=D(80_000_000), tuoi="99.99",
                  tl_hd=D(1), stone_value=D(10_000_000))
    r = evaluate(Case(old=[old], new=[], txn_date=TXN, prices=GOLD))
    assert r.total_value == D(8_000_000) + D(5_000_000)


def test_boundary_4ly_takes_lower_value():
    item = OldItem(rule_ids=("G2-KC-A", "G2-KC-D"), inv_date=date(2025, 12, 1), inv_value=D(100_000_000),
                   shell_value=D(20_000_000), kcr_stone_value=D(80_000_000), kcr_rule_ids=("G5-KCR-LT5",))
    r = evaluate(Case(old=[item], new=[NewItem(2, D(105_000_000))], txn_date=TXN))
    line = r.lines[0]
    assert line.value == D(90_000_000)  # dòng A (90%) thấp hơn dòng D (93tr)
    assert line.boundary_alt is not None and line.boundary_alt[1] == D(93_000_000)


def test_min_value_and_not_purchased_items():
    cam = OldItem(rule_ids=("G5-CAMTHACH",), inv_date=date(2025, 6, 1), inv_value=D(7_000_000))
    r = evaluate(Case(old=[cam], new=[], txn_date=TXN))
    assert r.total_value == 0
    cam.inv_value = D(10_000_000)
    assert evaluate(Case(old=[cam], new=[], txn_date=TXN)).total_value == D(5_000_000)
    lixi = OldItem(rule_ids=("G10-LIXI",), inv_date=date(2025, 6, 1), inv_value=D(1_000_000))
    assert evaluate(Case(old=[lixi], new=[], txn_date=TXN)).total_value == 0


def test_cam_ket_requires_ratio_input():
    old = OldItem(rule_ids=("G5-KCR-86-10",), inv_date=date(2018, 1, 1), inv_value=D(100_000_000))
    assert evaluate(Case(old=[old], new=[], txn_date=TXN)).incomplete
    old.cam_ket_ratio = D("0.9")
    assert evaluate(Case(old=[old], new=[], txn_date=TXN)).total_value == D(90_000_000)


def test_payout_schedule_sums_exactly():
    pg = payout_schedule(2, D(1_000_001))
    assert sum(r.amount for r in pg.rows) == D(1_000_001)
    assert payout_schedule(1, D(5)).rows[0].offset == "T+2"
    assert payout_schedule(3, D(5)).rows[0].offset == "T+7"


def test_two_items_mixed_eligibility():
    kcr = OldItem(rule_ids=("G5-KCR-6-86",), inv_date=date(2025, 6, 1), inv_value=D(50_000_000), name="KCR")
    charm = OldItem(rule_ids=("G10-CHARM",), inv_date=date(2025, 6, 1), inv_value=D(10_000_000), name="Charm")
    r = evaluate(Case(old=[kcr, charm], new=[NewItem(2, D(60_000_000))], txn_date=TXN))
    assert r.eligible == [True, False]
    assert r.lines[0].mode == "Đổi" and r.lines[1].mode == "Thu"
    assert r.total_value == D(49_000_000) + D(6_500_000)
    assert r.option == "PA1" and r.payout_total == D(6_500_000)  # charm vẫn là mua lại
    assert r.payouts[0].group == 10


def test_suggested_replies_cover_options():
    r = evaluate(kc_example(105_000_000))
    titles = [t for t, _ in suggest_replies(r)]
    assert any("Phương án 1" in t for t in titles)
    r = evaluate(kc_example(50_000_000))
    titles = [t for t, _ in suggest_replies(r)]
    assert any("Phương án 2" in t for t in titles) and any("Lộ trình" in t for t in titles)
    r = evaluate(Case(old=kc_example(0).old, new=[], txn_date=TXN))
    assert any("Phương án 3" in t for t, _ in suggest_replies(r))
