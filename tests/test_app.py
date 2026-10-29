"""Kiểm thử khói giao diện bằng Streamlit AppTest (không mở trình duyệt)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def run():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_app_loads_without_exception():
    at = run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4


def test_flow_pa1_kc_example():
    at = run()
    # Hàng cũ: dùng danh sách dòng hàng để tránh phụ thuộc helper
    at.radio(key="o0_how").set_value("Dòng hàng khác – chọn từ danh sách").run()
    at.selectbox(key="o0_rule").set_value("G2-VO").run()
    at.number_input(key="o0_inv").set_value(10_000_000).run()
    at.number_input(key="n0_value").set_value(20_000_000).run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.metric) if at.metric else ""
    assert any(m.label == "Giá trị thu đổi (cấn trừ)" and m.value == "8.500.000 đ" for m in at.metric), [ (m.label, m.value) for m in at.metric]
    assert any("Phương án 1" in s.value for s in at.success)


def test_flow_pa3_sell_back_only():
    at = run()
    at.radio(key="o0_how").set_value("Dòng hàng khác – chọn từ danh sách").run()
    at.selectbox(key="o0_rule").set_value("G2-VO").run()
    at.number_input(key="o0_inv").set_value(10_000_000).run()
    at.number_input(key="n_new").set_value(0).run()
    assert not at.exception, at.exception
    assert any("Phương án 3" in s.value for s in at.success)
    assert any(m.label == "PNJ chi trả cho khách" and m.value == "8.000.000 đ" for m in at.metric)


def test_missing_gold_price_shows_warning_not_crash():
    at = run()
    at.selectbox(key="o0_group").set_value(4).run()
    at.selectbox(key="o0_rule").set_value("G4-TUOIVANG").run()
    at.number_input(key="o0_inv").set_value(50_000_000).run()
    assert not at.exception, at.exception
    assert any("Chưa đủ dữ liệu" in w.value for w in at.warning)


def test_flow_kc_helper_matches_a2_example():
    """Ví dụ trong A2: KC 4,5ly VVS1, HĐ 100tr (vỏ 20tr + viên 80tr), mua mới 105tr → cấn trừ 93tr."""
    at = run()
    at.number_input(key="o0_inv").set_value(100_000_000).run()
    at.number_input(key="o0_shell").set_value(20_000_000).run()
    at.number_input(key="o0_kstone").set_value(80_000_000).run()
    at.number_input(key="n0_value").set_value(105_000_000).run()
    assert not at.exception, at.exception
    assert any(m.label == "Giá trị thu đổi (cấn trừ)" and m.value == "93.000.000 đ" for m in at.metric), [(m.label, m.value) for m in at.metric]
    assert any(m.label == "Khách thanh toán thêm" and m.value == "12.000.000 đ" for m in at.metric)


def test_non_hub_sidebar_warning():
    at = run()
    at.radio(key="o0_how").set_value("Dòng hàng khác – chọn từ danh sách").run()
    at.selectbox(key="o0_rule").set_value("G2-VO").run()
    at.number_input(key="o0_inv").set_value(10_000_000).run()
    at.number_input(key="n_new").set_value(0).run()
    at.radio(key="store").set_value("Cửa hàng thường (không phải HUB)").run()
    assert not at.exception, at.exception
    assert any("HUB" in e.value for e in at.error)
