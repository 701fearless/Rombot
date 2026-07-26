#!/usr/bin/env python3
"""Derive bounded, year-level traditional timing context from a timestamp."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
BRANCH_DEGREES = {
    "子": 0, "丑": 30, "寅": 60, "卯": 90, "辰": 120, "巳": 150,
    "午": 180, "未": 210, "申": 240, "酉": 270, "戌": 300, "亥": 330,
}
SAN_SHA = {
    "申": 180, "子": 180, "辰": 180,
    "寅": 0, "午": 0, "戌": 0,
    "亥": 270, "卯": 270, "未": 270,
    "巳": 90, "酉": 90, "丑": 90,
}
DIRECTION_NAMES = {0: "北", 90: "东", 180: "南", 270: "西"}
FALLBACK_TIMEZONES = {
    "Asia/Shanghai": timezone(timedelta(hours=8), "Asia/Shanghai"),
    "Etc/UTC": timezone.utc,
    "UTC": timezone.utc,
}


def parse_timestamp(value: str | None, timezone_name: str) -> tuple[datetime, str]:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        tz = FALLBACK_TIMEZONES.get(timezone_name)
        if tz is None:
            raise ValueError(
                f"Unknown IANA timezone without local tzdata: {timezone_name}"
            ) from exc
    if not value:
        return datetime.now(tz), "system-current-time"
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz), "input-localized-with-provided-timezone"
    return parsed.astimezone(tz), "input-timestamp"


def solar_year(dt: datetime) -> tuple[int, bool]:
    before_approx_li_chun = (dt.month, dt.day) < (2, 4)
    return (dt.year - 1 if before_approx_li_chun else dt.year), before_approx_li_chun


def ganzhi_year(year: int) -> tuple[str, str, str]:
    stem = STEMS[(year - 4) % 10]
    branch = BRANCHES[(year - 4) % 12]
    return stem + branch, stem, branch


def hour_branch(hour: int) -> str:
    return BRANCHES[((hour + 1) // 2) % 12]


def season_phase(dt: datetime) -> str:
    md = (dt.month, dt.day)
    if (2, 4) <= md < (5, 5):
        return "春季近似阶段"
    if (5, 5) <= md < (8, 7):
        return "夏季近似阶段"
    if (8, 7) <= md < (11, 7):
        return "秋季近似阶段"
    return "冬季近似阶段"


def period_for_year(year: int) -> dict[str, object]:
    if 2024 <= year <= 2043:
        return {"period": 9, "label": "下元九运", "range": [2024, 2043]}
    return {"period": None, "label": "outside bundled period lookup", "range": None}


def annual_directions(branch: str) -> dict[str, object]:
    tai_sui = BRANCH_DEGREES[branch]
    sui_po = (tai_sui + 180) % 360
    san_sha = SAN_SHA[branch]
    return {
        "taiSui": {"centerDeg": tai_sui, "branch": branch},
        "suiPo": {"centerDeg": sui_po},
        "sanSha": {"centerDeg": san_sha, "cardinalDirection": DIRECTION_NAMES[san_sha]},
        "usage": "secondary caution against unnecessary disturbance only",
    }


def build_context(timestamp: str | None, timezone_name: str) -> dict[str, object]:
    dt, source = parse_timestamp(timestamp, timezone_name)
    year, rolled_back = solar_year(dt)
    label, stem, branch = ganzhi_year(year)
    return {
        "asOf": dt.isoformat(),
        "timezone": timezone_name,
        "source": source,
        "yearContext": {
            "solarYearApprox": year,
            "ganzhi": label,
            "heavenlyStem": stem,
            "earthlyBranch": branch,
            "usedPreviousGregorianYear": rolled_back,
            "boundary": "approximate Li Chun at local date February 4",
        },
        "hourBranch": {
            "branch": hour_branch(dt.hour),
            "note": "earthly branch only; no hour stem or full pillars",
        },
        "season": {
            "phase": season_phase(dt),
            "precision": "approximate traditional seasonal gate",
        },
        "sanYuan": period_for_year(year),
        "annualDirections": annual_directions(branch),
        "precision": "year-level symbolic scaffold",
        "limitations": [
            "Exact Li Chun time is not calculated.",
            "Month, day, and hour pillars are not calculated.",
            "Annual directions require reliable north-angle data before spatial use.",
            "Do not use this output as a full almanac, fate reading, or prediction.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timestamp", help="ISO-8601 timestamp; defaults to now")
    parser.add_argument("--timezone", default="Asia/Shanghai", help="IANA timezone")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = build_context(args.timestamp, args.timezone)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
