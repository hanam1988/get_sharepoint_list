from tradein.kc import pick_kcr, pick_ts_kc

ROUND = "Tròn (KC trắng)"
FANCY = "Fancy (KC trắng)"
COLOR = "Kim cương màu"


def test_ts_kc_round_premium_by_size():
    assert pick_ts_kc(ROUND, "VVS1", 3.9).candidates == ("G2-KC-A",)
    assert pick_ts_kc(ROUND, "VVS1", 4.5).candidates == ("G2-KC-D",)


def test_ts_kc_boundary_returns_both_rows():
    p = pick_ts_kc(ROUND, "VS1", 4)
    assert p.boundary and set(p.candidates) == {"G2-KC-A", "G2-KC-D"}
    p = pick_ts_kc(FANCY, "VS1", 3.5)
    assert p.boundary and set(p.candidates) == {"G2-KC-B", "G2-KC-C"}


def test_ts_kc_lower_clarity_and_color_use_general_row():
    assert pick_ts_kc(ROUND, "SI1", 6).candidates == ("G2-KC-A",)
    assert pick_ts_kc(COLOR, "VS1", 8).candidates == ("G2-KC-A",)


def test_kcr_tiers():
    assert pick_kcr(ROUND, "VVS1", 4.5).candidates == ("G5-KCR-LT5",)
    assert pick_kcr(ROUND, "VS1", 5.5).candidates == ("G5-KCR-5-6",)
    assert pick_kcr(ROUND, "VS1", 7).candidates == ("G5-KCR-6-86",)
    assert pick_kcr(ROUND, "VS1", 9).candidates == ("G5-KCR-86-10",)
    assert pick_kcr(ROUND, "VS1", 12).candidates == ("G5-KCR-10UP",)


def test_kcr_boundaries():
    for size, pair in [(5, {"G5-KCR-5-6", "G5-KCR-LT5"}), (6, {"G5-KCR-6-86", "G5-KCR-5-6"}),
                       (8.6, {"G5-KCR-86-10", "G5-KCR-6-86"}), (10, {"G5-KCR-10UP", "G5-KCR-86-10"})]:
        p = pick_kcr(ROUND, "VS1", size)
        assert p.boundary and set(p.candidates) == pair, size


def test_kcr_si_and_unsupported():
    assert pick_kcr(ROUND, "SI1", 7).candidates == ("G5-KCR-SI-GE6",)
    assert pick_kcr(ROUND, "SI2", 5).candidates == ("G5-KCR-SI-LT6",)
    assert pick_kcr(ROUND, "VS2", 5) is None  # A2 không có dòng VS2
    assert pick_kcr(FANCY, "VS1", 5) is None
    assert pick_kcr(COLOR, "VS1", 5).candidates == ("G5-KC-MAU",)
