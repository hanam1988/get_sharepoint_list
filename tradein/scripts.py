"""Gợi ý câu trả lời cho tư vấn viên, dựa trên kết quả tính. Mẫu câu cố định, có dẫn căn cứ văn bản."""
from __future__ import annotations

from decimal import Decimal

from .calc import CaseResult


def vnd(x: Decimal | int | None) -> str:
    if x is None:
        return "chưa xác định"
    return f"{Decimal(x):,.0f}".replace(",", ".") + " đ"


def suggest_replies(result: CaseResult) -> list[tuple[str, str]]:
    """Trả về danh sách (tiêu đề, nội dung) để TVV tham khảo khi nói với khách."""
    if result.incomplete:
        return [("Cần thêm thông tin", "Anh/chị cho em xin thêm thông tin về sản phẩm (trọng lượng, loại đá, ngày hóa đơn) để em tính chính xác giá trị thu đổi ạ.")]

    replies: list[tuple[str, str]] = []
    mode = "tỷ lệ Đổi" if result.doi_applies else "tỷ lệ Thu"
    replies.append((
        "Giá trị sản phẩm cũ",
        f"Theo chính sách thu đổi hiện hành, sản phẩm cũ của anh/chị được tính {vnd(result.total_value)} (áp dụng {mode}). "
        + ("Mức này áp dụng vì anh/chị chọn mua sản phẩm mới có giá trị từ giá trị hóa đơn cũ trở lên." if result.doi_applies else "Nếu anh/chị chọn mua sản phẩm mới thuộc nhóm được chuyển đổi và có giá trị từ giá trị hóa đơn cũ trở lên thì sẽ được áp dụng tỷ lệ Đổi cao hơn."),
    ))

    if result.option == "PA1":
        replies.append((
            "Phương án 1 – chuyển đổi toàn bộ",
            f"Anh/chị sử dụng toàn bộ giá trị sản phẩm cũ ({vnd(result.total_value)}) để mua sản phẩm mới, thanh toán thêm {vnd(result.customer_pays)}. Giao dịch này làm được tại mọi cửa hàng PNJ.",
        ))
    elif result.option == "PA2":
        replies.append((
            "Phương án 2 – chuyển đổi một phần",
            f"Anh/chị dùng một phần giá trị sản phẩm cũ để mua sản phẩm mới. Phần còn lại {vnd(result.payout_total)} PNJ chi trả bằng tiền theo lộ trình thanh toán của từng dòng hàng. "
            "Giao dịch này thực hiện tại cửa hàng HUB, trong khung giờ 15h00–17h00, và em sẽ in Phụ lục 01 Thỏa thuận thu đổi sản phẩm để anh/chị xem kỹ và ký xác nhận.",
        ))
    elif result.option == "PA3":
        replies.append((
            "Phương án 3 – mua lại hoàn toàn",
            f"PNJ mua lại sản phẩm với giá trị {vnd(result.total_value)} và chi trả theo lộ trình thanh toán của từng dòng hàng. "
            "Giao dịch này thực hiện tại cửa hàng HUB, trong khung giờ 15h00–17h00.",
        ))

    for pg in result.payouts:
        if len(pg.rows) == 1:
            plan = f"thanh toán toàn bộ {vnd(pg.amount)} vào {pg.rows[0].offset}"
        else:
            plan = "; ".join(f"{r.pct}% ({vnd(r.amount)}) vào {r.offset}" for r in pg.rows)
        replies.append((f"Lộ trình chi trả – nhóm {pg.group}", f"Với sản phẩm thuộc nhóm {pg.group}, PNJ {plan}, tính từ ngày giao dịch (T)."))

    if result.option in ("PA2", "PA3") and result.payout_total > 0:
        replies.append((
            "Cam kết của PNJ",
            "PNJ cam kết thực hiện đầy đủ nghĩa vụ thanh toán đối với giao dịch đã được tiếp nhận và xác lập đúng chính sách, điều kiện và lộ trình đã thông báo. "
            "Cửa hàng có Thông báo về hồ sơ giao dịch mua hàng giữa PNJ và khách hàng có mộc đỏ để anh/chị tham khảo.",
        ))

    refused = [l for l in result.lines if l.method.startswith(("Không thu mua", "Dưới mức tối thiểu"))]
    for l in refused:
        replies.append((f"Sản phẩm không thu mua – {l.label}", "Rất tiếc, theo quy định hiện hành sản phẩm này chưa nằm trong diện thu mua nên em chưa thể nhận thu đổi ạ."))
    return replies
