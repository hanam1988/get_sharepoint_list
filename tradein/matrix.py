"""Nhóm hàng, ma trận chuyển đổi và lộ trình thanh toán (data/matrix.yaml)."""
from __future__ import annotations

from datetime import time
from functools import lru_cache

import yaml

from .rules import DATA_DIR


@lru_cache(maxsize=1)
def _raw() -> dict:
    return yaml.safe_load((DATA_DIR / "matrix.yaml").read_text(encoding="utf-8"))


def documents() -> dict:
    return _raw()["documents"]


def groups() -> dict[int, dict]:
    return {int(k): v for k, v in _raw()["groups"].items()}


def group_label(group: int) -> str:
    g = groups()[group]
    return f"Nhóm {group} – {g['name']}"


def conversion() -> dict[int, list[int]]:
    return {int(k): list(v) for k, v in _raw()["conversion"].items()}


def allowed_new_groups(old_group: int) -> list[int]:
    return conversion().get(old_group, [])


def schedule_for_group(group: int) -> dict:
    key = groups()[group]["schedule"]
    return _raw()["schedules"][key]


def legacy_t120() -> dict:
    raw = _raw()
    return {"paid_in_full": raw["legacy_t120_paid_in_full"], "keep_schedule": raw["legacy_t120_keep_schedule"]}


def _parse_hhmm(text: str) -> time:
    hh, mm = text.split(":")
    return time(int(hh), int(mm))


def buyback_window() -> tuple[time, time]:
    cfg = _raw()["transaction"]
    return _parse_hhmm(cfg["buyback_window_start"]), _parse_hhmm(cfg["buyback_window_stop"])


def in_buyback_window(t: time) -> bool:
    start, stop = buyback_window()
    return start <= t < stop
