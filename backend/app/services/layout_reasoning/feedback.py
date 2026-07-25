from __future__ import annotations

from app.schemas import CheckDetail, PlacementCandidate


STATUS_RANK = {"pass": 0, "warn": 1, "fail": 2}


def overall_status(checks: list[CheckDetail]) -> str:
    rank = max((STATUS_RANK.get(item.status, 0) for item in checks), default=0)
    for key, value in STATUS_RANK.items():
        if value == rank:
            return key
    return "pass"


def compose_feedback(candidate: PlacementCandidate, checks: list[CheckDetail]) -> str:
    """把四项检测结果整理成自然语言（确定性模板，不调用 LLM）。"""
    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]
    problems = fails + warns

    if not problems:
        return f"{candidate.name}可以放入当前房间，四项基础空间检测均通过，可正常使用。"

    issue_texts: list[str] = []
    for index, check in enumerate(problems, start=1):
        issue_texts.append(f"{'一二三四五六七八九十'[index - 1] if index <= 10 else index}是{check.message}")

    prefix = f"该{candidate.name}可以尝试放入当前房间，但存在{len(problems)}处问题："
    if any(c.ruleId == "fit" and c.status == "fail" for c in fails):
        prefix = f"该{candidate.name}在当前目标位置存在摆放问题："

    body = "，".join(issue_texts) + "。"

    suggestions = [c.suggestion for c in problems if c.suggestion]
    advice = ""
    if suggestions:
        # Prefer a concise combined suggestion.
        advice = "建议" + _merge_suggestions(suggestions)

    return prefix + body + advice


def _merge_suggestions(suggestions: list[str]) -> str:
    cleaned: list[str] = []
    for text in suggestions:
        item = text.strip()
        for prefix in ("建议", "该家具", "该位置", "当前摆放区域空间不足，建议"):
            if item.startswith(prefix):
                item = item[len(prefix) :]
                break
        item = item.strip(" 。")
        if item and item not in cleaned:
            cleaned.append(item)
    if not cleaned:
        return "调整摆放位置后再试。"
    if len(cleaned) == 1:
        return cleaned[0] if cleaned[0].endswith("。") else cleaned[0] + "。"
    return "；".join(cleaned) + "。"
