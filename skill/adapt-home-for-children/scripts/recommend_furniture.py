#!/usr/bin/env python3
"""Rank 1-2 furniture products from a JSON catalog without inventing attributes."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


DOMAIN_TERMS = {
    "fengshui": ["风水", "有靠", "收纳", "暖光", "圆润", "稳定", "床", "灯", "柜", "屏风", "地毯"],
    "child": ["儿童", "婴儿", "适儿", "圆角", "防倾倒", "可清洗", "收纳", "软包", "防滑"],
    "pet": ["宠物", "猫", "狗", "耐抓", "耐磨", "耐咬", "可清洗", "防滑", "窝", "收纳"],
}


def load_catalog(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return {"catalogId": path.stem}, data
    if not isinstance(data, dict):
        raise ValueError("catalog must be an object or an array")
    items = data.get("items", data.get("furniture", data.get("products")))
    if not isinstance(items, list):
        raise ValueError("catalog must contain an items, furniture, or products array")
    return data, items


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(as_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {as_text(item)}" for key, item in value.items())
    return ""


def pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def dimensions_complete(item: dict[str, Any]) -> bool:
    dims = item.get("dimensions")
    if not isinstance(dims, dict):
        return False
    return all(isinstance(dims.get(key), (int, float)) and math.isfinite(dims[key]) and dims[key] > 0
               for key in ("width", "depth", "height")) and bool(dims.get("unit"))


def structured_score(item: dict[str, Any], domain: str, age_months: int | None, species: str | None) -> tuple[float, list[str], list[str], bool]:
    score = 0.0
    reasons: list[str] = []
    verify: list[str] = []
    eligible = True

    if item.get("availability") == "out_of_stock":
        return -1000, ["库存状态为缺货"], [], False

    if dimensions_complete(item):
        score += 2
        reasons.append("目录提供完整尺寸，可进一步验证落位")
    else:
        verify.append("缺少完整尺寸，不能自动落位")

    if domain == "child":
        safety = item.get("generalSafety") or {}
        child = item.get("childSuitability") or {}
        if safety.get("roundedEdges") is True:
            score += 3
            reasons.append("JSON 明确标注圆角")
        elif safety.get("roundedEdges") is None:
            verify.append("核验边角形态")
        if safety.get("tipOverTested") is True:
            score += 4
            reasons.append("JSON 明确标注已做防倾倒测试")
        elif item.get("placement", {}).get("requiresAnchoring") is True:
            verify.append("按产品说明完成固定后才能使用")
        else:
            verify.append("核验倾倒风险与固定要求")
        for key, label in (("smallPartsRisk", "小零件"), ("entrapmentRisk", "夹困"),
                           ("cordRisk", "绳线"), ("climbRisk", "攀爬")):
            value = child.get(key)
            if value == "high":
                score -= 8
                eligible = False
                reasons.append(f"JSON 标注{label}风险高")
            elif value == "low":
                score += 2
                reasons.append(f"JSON 标注{label}风险低")
            elif value in (None, "unknown"):
                verify.append(f"核验{label}风险")
        age = child.get("recommendedAgeMonths")
        if age_months is not None and isinstance(age, dict):
            lower, upper = age.get("min"), age.get("max")
            if isinstance(lower, int) and age_months < lower or isinstance(upper, int) and age_months > upper:
                eligible = False
                reasons.append("年龄不在 JSON 标注的建议范围内")

    elif domain == "pet":
        pet = item.get("petSuitability") or {}
        species_list = [str(value).lower() for value in pet.get("species", [])]
        if species and species_list and species.lower() not in species_list:
            eligible = False
            reasons.append("物种不在 JSON 标注的适用范围内")
        for key, label in (("scratchResistance", "耐抓"), ("chewResistance", "耐咬")):
            value = pet.get(key)
            if value == "high":
                score += 3
                reasons.append(f"JSON 标注{label}等级高")
            elif value == "low":
                score -= 2
            elif value in (None, "unknown"):
                verify.append(f"核验{label}性能")
        for key, label in (("washable", "可清洗"), ("replaceableCover", "可替换外套"),
                           ("antiSlip", "防滑"), ("nonToxicMaterialClaim", "无毒材料声明")):
            if pet.get(key) is True:
                score += 2
                reasons.append(f"JSON 明确标注{label}")
            elif pet.get(key) is None:
                verify.append(f"核验{label}")

    elif domain == "fengshui":
        traits = item.get("fengshuiTraits") or {}
        if traits.get("backingSupport") is True:
            score += 3
            reasons.append("JSON 标注可提供稳定背部支撑")
        if traits.get("reflective") is False:
            score += 1
            reasons.append("JSON 标注为非反光表面")
        if traits.get("lightType"):
            score += 1
            reasons.append("目录提供光型，可与空间照明问题匹配")
        if not traits:
            verify.append("缺少风水布置特征，只能按品类和描述低置信度推荐")

    claims = item.get("claims") or []
    verified_claims = [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "verified"]
    if verified_claims:
        score += min(2, len(verified_claims))
        reasons.append(f"含 {len(verified_claims)} 项已验证声明")
    return score, reasons, sorted(set(verify)), eligible


def rank(catalog_path: Path, domain: str, needs: list[str], max_items: int,
         age_months: int | None, species: str | None) -> dict[str, Any]:
    metadata, items = load_catalog(catalog_path)
    if not items:
        return {
            "status": "catalog_empty",
            "catalogPath": str(catalog_path),
            "catalogId": metadata.get("catalogId"),
            "recommendations": [],
            "message": "家具目录为空；请补充商品 JSON 后再生成 1-2 件推荐。",
        }

    terms = DOMAIN_TERMS[domain] + [term for need in needs for term in need.split() if term]
    ranked: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("id") or not item.get("title"):
            continue
        score, reasons, verify, eligible = structured_score(item, domain, age_months, species)
        if not eligible:
            continue
        blob = as_text(item).lower()
        matched = sorted({term for term in terms if term and term.lower() in blob})
        score += len(matched) * 1.5
        if matched:
            reasons.append("匹配 JSON 关键词：" + "、".join(matched[:8]))
        item_id = str(item["id"])
        ranked.append({
            "productId": item_id,
            "title": item["title"],
            "category": item.get("category"),
            "score": round(score, 2),
            "reasons": reasons or ["目录中可用的候选商品"],
            "evidenceRefs": [
                f"{catalog_path}#/items/{index}/id",
                f"{catalog_path}#/items/{index}",
            ],
            "verificationRequired": verify,
            "placementEligible": dimensions_complete(item),
            "dimensions": item.get("dimensions"),
            "priceRefs": item.get("priceRefs", []),
        })

    ranked.sort(key=lambda value: (-value["score"], value["productId"]))
    recommendations = ranked[:max_items]
    return {
        "status": "ok" if recommendations else "no_eligible_products",
        "catalogPath": str(catalog_path),
        "catalogId": metadata.get("catalogId"),
        "domain": domain,
        "needs": needs,
        "recommendations": [dict(rank=index + 1, **item) for index, item in enumerate(recommendations)],
        "selectionPolicy": "JSON evidence only; unknown attributes remain verification items",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--domain", required=True, choices=sorted(DOMAIN_TERMS))
    parser.add_argument("--need", action="append", default=[])
    parser.add_argument("--max-items", type=int, choices=(1, 2), default=2)
    parser.add_argument("--age-months", type=int)
    parser.add_argument("--species")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = rank(args.catalog, args.domain, args.need, args.max_items, args.age_months, args.species)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"status": "error", "recommendations": [], "error": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
