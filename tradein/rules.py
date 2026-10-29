"""Tải và áp dụng quy tắc thu đổi từ data/rules.yaml (quy tắc là dữ liệu, không viết cứng trong code)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Token không phải là tỷ lệ số.
TOKENS = {"NL", "NL_THU", "KHONG", "CAM_KET_HD", "CAN_DUYET", "REF_CT", "REF_A15", "REF_A16"}
REF_TOKENS = {"REF_CT": "chương trình thu mua của Khối Cung ứng", "REF_A15": "PL A15", "REF_A16": "PL A16"}

Token = Decimal | str


def to_token(value) -> Token | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return str(value)


def _d(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _iso(value) -> date | None:
    if value is None:
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value))


@dataclass(frozen=True)
class Rule:
    id: str
    payment_group: int
    label: str
    source: str
    kind: str | None = None  # None | "weight_split" | "split_shell_stone"
    thu: Token | None = None
    doi: Token | None = None
    periods: tuple[dict, ...] = ()
    age_tiers: tuple[dict, ...] = ()
    legacy: dict | None = None
    min_value: Decimal | None = None
    stone_factor: Decimal | None = None
    combo_doi: Decimal | None = None
    shell_thu: Decimal | None = None
    shell_doi: Decimal | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Resolved:
    """Kết quả áp dụng quy tắc cho một hóa đơn cụ thể."""

    thu: Token
    doi: Token
    stone_factor: Decimal | None
    notes: tuple[str, ...]
    alt: dict | None = None


def _rule_from_dict(raw: dict) -> Rule:
    return Rule(
        id=raw["id"],
        payment_group=int(raw["payment_group"]),
        label=raw["label"],
        source=raw.get("source", ""),
        kind=raw.get("kind"),
        thu=to_token(raw.get("thu")),
        doi=to_token(raw.get("doi")),
        periods=tuple(raw.get("periods", ())),
        age_tiers=tuple(raw.get("age_tiers", ())),
        legacy=raw.get("legacy"),
        min_value=_d(raw.get("min_value")),
        stone_factor=_d(raw.get("stone_factor")),
        combo_doi=_d(raw.get("combo_doi")),
        shell_thu=_d(raw.get("shell_thu")),
        shell_doi=_d(raw.get("shell_doi")),
        notes=tuple(raw.get("notes", ())),
    )


@lru_cache(maxsize=1)
def load_rules(path: str | None = None) -> dict[str, Rule]:
    file = Path(path) if path else DATA_DIR / "rules.yaml"
    raw = yaml.safe_load(file.read_text(encoding="utf-8"))
    rules = [_rule_from_dict(r) for r in raw["rules"]]
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("rules.yaml có id trùng nhau")
    return {r.id: r for r in rules}


@lru_cache(maxsize=1)
def rules_meta() -> dict:
    raw = yaml.safe_load((DATA_DIR / "rules.yaml").read_text(encoding="utf-8"))
    return {"version": raw.get("version"), "effective_from": raw.get("effective_from")}


def rules_of_group(group: int) -> list[Rule]:
    return [r for r in load_rules().values() if r.payment_group == group]


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29/02
        return d.replace(year=d.year + years, day=28)


def resolve(rule: Rule, inv_date: date, txn_date: date) -> Resolved:
    """Xác định tỷ lệ/cách tính Thu và Đổi của một dòng hàng theo ngày HĐ."""
    notes = list(rule.notes)

    if rule.legacy and inv_date < _iso(rule.legacy["before"]):
        before = _iso(rule.legacy["before"]).strftime("%d/%m/%Y")
        notes.append(f"HĐ xuất bán trước {before}: thu đổi theo chính sách cam kết trên HĐ / chính sách trích lục theo HĐ.")
        token = rule.legacy["token"]
        return Resolved(token, token, rule.stone_factor, tuple(notes))

    if rule.age_tiers:
        for tier in rule.age_tiers:
            max_years = tier.get("max_years")
            if max_years is None or txn_date <= add_years(inv_date, int(max_years)):
                return Resolved(to_token(tier["thu"]), to_token(tier["doi"]), rule.stone_factor, tuple(notes))

    if rule.periods:
        for period in rule.periods:
            start, end = _iso(period.get("from")), _iso(period.get("to"))
            if (start is None or inv_date >= start) and (end is None or inv_date <= end):
                if period.get("note"):
                    notes.append(period["note"])
                stone = _d(period["stone_factor"]) if "stone_factor" in period else rule.stone_factor
                alt = period.get("alt")
                if alt:
                    alt = {"label": alt["label"], "thu": to_token(alt["thu"]), "doi": to_token(alt["doi"])}
                return Resolved(to_token(period["thu"]), to_token(period["doi"]), stone, tuple(notes), alt)
        raise ValueError(f"{rule.id}: không có giai đoạn nào khớp ngày HĐ {inv_date}")

    return Resolved(rule.thu, rule.doi, rule.stone_factor, tuple(notes))


def fmt_token(token: Token | None) -> str:
    if token is None:
        return "-"
    if isinstance(token, Decimal):
        return f"{(token * 100).normalize():f}%"
    return {
        "NL": "Theo giá nguyên liệu",
        "NL_THU": "Thu theo giá nguyên liệu",
        "KHONG": "Không thu mua",
        "CAM_KET_HD": "Theo cam kết trên HĐ",
        "CAN_DUYET": "Chỉ khi được duyệt",
        "REF_CT": "Theo chương trình thu mua",
        "REF_A15": "Tra PL A15",
        "REF_A16": "Tra PL A16",
    }.get(token, token)


def describe_rule(rule: Rule) -> list[dict]:
    """Mô tả quy tắc dạng bảng để hiển thị (mỗi dòng một giai đoạn / một bậc thời gian)."""
    rows: list[dict] = []
    if rule.kind == "split_shell_stone":
        rows.append({"Áp dụng cho": "Mọi HĐ", "Thu": f"Vỏ {fmt_token(rule.shell_thu)}; viên theo KCR", "Đổi": f"Vỏ {fmt_token(rule.shell_doi)}; viên theo KCR"})
    elif rule.age_tiers:
        for tier in rule.age_tiers:
            label = f"Trong vòng {tier['max_years']} năm kể từ ngày HĐ" if tier.get("max_years") else "Quá thời hạn trên"
            rows.append({"Áp dụng cho": label, "Thu": fmt_token(to_token(tier["thu"])), "Đổi": fmt_token(to_token(tier["doi"]))})
    elif rule.periods:
        for p in rule.periods:
            start, end = _iso(p.get("from")), _iso(p.get("to"))
            if start and end:
                label = f"HĐ từ {start:%d/%m/%Y} đến {end:%d/%m/%Y}"
            elif start:
                label = f"HĐ từ {start:%d/%m/%Y}"
            elif end:
                label = f"HĐ đến hết {end:%d/%m/%Y}"
            else:
                label = "Mọi HĐ"
            rows.append({"Áp dụng cho": label, "Thu": fmt_token(to_token(p["thu"])), "Đổi": fmt_token(to_token(p["doi"]))})
    else:
        rows.append({"Áp dụng cho": "Mọi HĐ", "Thu": fmt_token(rule.thu), "Đổi": fmt_token(rule.doi)})
    if rule.legacy:
        rows.insert(0, {"Áp dụng cho": f"HĐ trước {_iso(rule.legacy['before']):%d/%m/%Y}", "Thu": fmt_token(rule.legacy["token"]), "Đổi": fmt_token(rule.legacy["token"])})
    return rows
