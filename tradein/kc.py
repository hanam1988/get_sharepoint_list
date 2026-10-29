"""Xác định dòng hàng kim cương theo đặc điểm đá (hình dáng, độ sạch, cỡ lớn nhất).

PL A2 có các khoảng kích thước chồng lấn ở giá trị biên (ví dụ "≤4ly" và "từ 4ly↑").
Mặc định của app: tại đúng giá trị biên, trả về CẢ HAI dòng để tính; kết quả lấy giá trị thấp hơn.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

SHAPES = ["Tròn (KC trắng)", "Fancy (KC trắng)", "Kim cương màu"]
CLARITIES = ["FL", "IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2", "I1", "I2", "I3", "Khác (AAA/AA/A/KQT)"]

# TS kim cương: nhóm chất lượng cao được hưởng dòng riêng khi cỡ ≥4ly.
TS_PREMIUM = {"IF", "FL", "VVS1", "VS1"}
# KCR: "từ VS1/VVS1 trở lên" gồm cả VVS2.
KCR_PREMIUM = {"IF", "FL", "VVS1", "VVS2", "VS1"}
KCR_SI = {"SI1", "SI2"}


@dataclass(frozen=True)
class Pick:
    candidates: tuple[str, ...]  # 1 dòng; 2 dòng khi đúng giá trị biên
    note: str = ""
    boundary: bool = False


def _dec(x) -> Decimal:
    return Decimal(str(x))


def pick_ts_kc(shape: str, clarity: str, size) -> Pick:
    """Dòng hàng cho TS kim cương (nhóm thanh toán 2)."""
    size = _dec(size)
    if shape == "Kim cương màu":
        return Pick(("G2-KC-A",))
    if shape == "Fancy (KC trắng)":
        if size < Decimal("3.5"):
            return Pick(("G2-KC-B",))
        if size == Decimal("3.5"):
            return Pick(("G2-KC-B", "G2-KC-C"), "Cỡ đúng 3,5ly nằm ở biên của hai dòng; app tính cả hai và lấy giá trị thấp hơn.", True)
        return Pick(("G2-KC-C",))
    # Tròn trắng
    if clarity not in TS_PREMIUM:
        return Pick(("G2-KC-A",), "Tròn VVS2…KQT mọi cỡ thuộc dòng chung.")
    if size < 4:
        return Pick(("G2-KC-A",))
    if size == 4:
        return Pick(("G2-KC-A", "G2-KC-D"), "Cỡ đúng 4ly nằm ở biên của hai dòng; app tính cả hai và lấy giá trị thấp hơn.", True)
    return Pick(("G2-KC-D",), "Cần tách giá trị vỏ và giá trị viên trên HĐ.")


def pick_kcr(shape: str, clarity: str, size) -> Pick | None:
    """Dòng hàng cho kim cương rời (nhóm thanh toán 5). None nếu A2 không có dòng phù hợp."""
    size = _dec(size)
    if shape == "Kim cương màu":
        return Pick(("G5-KC-MAU",))
    if shape != "Tròn (KC trắng)":
        return None
    if clarity in KCR_PREMIUM:
        tiers = [  # (cận dưới, rule) theo thứ tự giảm dần
            (Decimal("10"), "G5-KCR-10UP"),
            (Decimal("8.6"), "G5-KCR-86-10"),
            (Decimal("6"), "G5-KCR-6-86"),
            (Decimal("5"), "G5-KCR-5-6"),
        ]
        lowest = "G5-KCR-LT5"
        ordered = tiers + [(Decimal("0"), lowest)]
        for i, (floor, rule_id) in enumerate(ordered):
            if size > floor or (floor == 0):
                return Pick((rule_id,))
            if size == floor:
                lower = ordered[i + 1][1]
                return Pick((rule_id, lower), f"Cỡ đúng {floor}ly nằm ở biên của hai dòng; app tính cả hai và lấy giá trị thấp hơn.", True)
        return Pick((lowest,))
    if clarity in KCR_SI:
        if size > 6:
            return Pick(("G5-KCR-SI-GE6",))
        if size == 6:
            return Pick(("G5-KCR-SI-GE6", "G5-KCR-SI-LT6"), "Cỡ đúng 6ly nằm ở biên của hai dòng; app tính cả hai và lấy giá trị thấp hơn.", True)
        return Pick(("G5-KCR-SI-LT6",))
    return None
