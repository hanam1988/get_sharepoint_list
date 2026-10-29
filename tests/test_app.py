"""Kiểm thử khói giao diện bằng Streamlit AppTest (không mở trình duyệt)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
OTHER_ROW = "Dòng hàng khác – chọn từ danh sách"


def run() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def old_vo(at: AppTest, inv: int = 10_000_000) -> None:
    """Hàng cũ: nhóm 2, dòng TS vỏ."""
    at.selectbox(key="o0_group").set_value(2).run()
    at.radio(key="o0_how").set_value(OTHER_ROW).run()
    at.selectbox(key="o0_rule").set_value("G2-VO").run()
    at.number_input(key="o0_inv").set_value(inv).run()


def metric(at: AppTest, label: str) -> str | None:
    return next((m.value for m in at.metric if m.label == label), None)


def test_app_loads_without_exception():
    at = run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4
    assert any("Chọn nhóm hàng" in i.value for i in at.info)  # chưa chọn gì thì chỉ nhắc nhập


def test_layout_has_two_sections_with_totals():
    at = run()
    heads = " ".join(m.value for m in at.markdown)
    assert "1. Hàng cũ thu đổi / mua lại (Bảng kê)" in heads
    assert "2. Hàng mới khách mua (Hóa đơn)" in heads
    assert "0 VNĐ" in heads
    old_vo(at)
    at.number_input(key="n0_value").set_value(7_000_000).run()
    heads = " ".join(m.value for m in at.markdown)
    assert "10.000.000 VNĐ" in heads and "7.000.000 VNĐ" in heads


def test_flow_pa1():
    at = run()
    old_vo(at)
    at.selectbox(key="n0_group").set_value(2).run()
    at.number_input(key="n0_value").set_value(20_000_000).run()
    assert not at.exception, at.exception
    assert metric(at, "Giá trị thu đổi (cấn trừ)") == "8.500.000 đ"  # TS vỏ: Đổi 85%
    assert any("Phương án 1" in s.value for s in at.success)


def test_flow_pa3_sell_back_only_after_deleting_new_row():
    at = run()
    old_vo(at)
    at.button(key="n0_del").click().run()
    assert not at.exception, at.exception
    assert any("Phương án 3" in s.value for s in at.success)
    assert metric(at, "PNJ chi trả cho khách") == "8.000.000 đ"  # TS vỏ: Thu 80%


def test_add_and_remove_rows():
    at = run()
    at.button(key="old_add").click().run()
    assert at.selectbox(key="o1_group") is not None
    at.button(key="o1_del").click().run()
    assert not [s for s in at.selectbox if s.key == "o1_group"]
    at.button(key="new_add").click().run()
    assert at.selectbox(key="n1_group") is not None
    assert not at.exception, at.exception


def test_missing_gold_price_shows_warning_not_crash():
    at = run()
    at.selectbox(key="o0_group").set_value(4).run()
    at.number_input(key="o0_inv").set_value(50_000_000).run()
    assert not at.exception, at.exception
    assert any("Chưa đủ dữ liệu" in w.value for w in at.warning)


def test_flow_kc_helper_matches_a2_example():
    """Ví dụ trong A2: KC 4,5ly VVS1, HĐ 100tr (vỏ 20tr + viên 80tr), mua mới 105tr → cấn trừ 93tr."""
    at = run()
    at.selectbox(key="o0_group").set_value(2).run()  # mặc định: xác định theo đặc điểm đá (tròn, VVS1, 4,5ly)
    at.number_input(key="o0_inv").set_value(100_000_000).run()
    at.number_input(key="o0_shell").set_value(20_000_000).run()
    at.number_input(key="o0_kstone").set_value(80_000_000).run()
    at.selectbox(key="n0_group").set_value(2).run()
    at.number_input(key="n0_value").set_value(105_000_000).run()
    assert not at.exception, at.exception
    assert metric(at, "Giá trị thu đổi (cấn trừ)") == "93.000.000 đ"
    assert metric(at, "Khách thanh toán thêm") == "12.000.000 đ"


def test_non_hub_warning():
    at = run()
    old_vo(at)
    at.button(key="n0_del").click().run()
    at.radio(key="store").set_value("Cửa hàng thường (không phải HUB)").run()
    assert not at.exception, at.exception
    assert any("HUB" in e.value for e in at.error)
