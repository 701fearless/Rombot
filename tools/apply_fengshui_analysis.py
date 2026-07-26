import argparse
import copy
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with args.source.open("r", encoding="utf-8") as handle:
        original = json.load(handle)

    data = copy.deepcopy(original)
    as_of = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    compact_stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%dT%H%M%S%z")

    analysis = {
        "analysisId": f"fs-{compact_stamp}",
        "asOf": as_of,
        "sourceFile": str(args.source),
        "inputCompleteness": "geometry-partial",
        "methods": ["physical", "form"],
        "fieldMapping": {
            "units": "/floorplan/room/unit",
            "roomEnvelope": "/floorplan/room",
            "embeddedBuildingGeometry": "/floorplan/glbBase64",
            "furnitureCandidates": "/deduplicatedObjects",
            "furniturePosition": "/deduplicatedObjects/*/transform/position",
            "furnitureScale": "/deduplicatedObjects/*/transform/size",
            "furnitureEstimatedDimensions": "/deduplicatedObjects/*/estimatedDimensions",
        },
        "limitations": [
            "输入没有标准 rooms、furniture、门窗开启区、通道约束和北向字段，原版校验器无法完成边界、碰撞与通行验证。",
            "建筑边界和门窗语义仅存在于嵌入式 GLB；JSON 没有可直接引用的房间多边形。",
            "9 件家居的 estimatedDimensions.isMeasured 均为 false，且估算值高度一致，不能据此自动移动或新增实体。",
            "deduplicatedObjects 使用 candidate_* 名称；除镜子外 isSelected 均为 false，需确认它们是已落位物件还是候选预览。",
            "缺少北向角，因此不做东南西北、八宅、飞星或流年落位判断。",
        ],
        "spaceValiditySummary": {
            "jsonParse": "passed",
            "declaredRoomEnvelopeM": {
                "width": 5.9825,
                "depth": 10.500000000000002,
                "unit": "m",
                "evidenceRefs": ["/floorplan/room"],
            },
            "embeddedGltf": {
                "nodeCount": 191,
                "meshCount": 167,
                "observedSemanticElements": [
                    "entry door",
                    "kitchen door and window",
                    "bedroom A door and windows",
                    "bedroom B door",
                    "bathroom door and window",
                    "balcony sliding door and window",
                ],
                "evidenceRefs": ["/floorplan/glbBase64"],
            },
            "furnitureCandidateCount": 9,
            "coordinateChangesAllowed": False,
        },
        "issues": [
            {
                "id": "issue-schema-not-validatable",
                "priority": "P0 safety",
                "status": "observed",
                "confidence": 1.0,
                "method": "physical",
                "evidenceRefs": [
                    "/floorplan/room",
                    "/floorplan/glbBase64",
                    "/deduplicatedObjects",
                ],
                "summary": "布局未映射为校验器要求的 rooms/furniture 模型，当前不能证明边界、碰撞、门扇与连续通道安全。",
                "falsifiers": ["补充标准化 rooms、furniture、门窗开启区和通道约束后重新校验通过。"],
            },
            {
                "id": "issue-bed-in-kitchen-semantic-zone",
                "priority": "P1 strong",
                "status": "inferred",
                "confidence": 0.82,
                "method": "physical",
                "evidenceRefs": [
                    "/deduplicatedObjects/6/name",
                    "/deduplicatedObjects/6/transform/position",
                    "/deduplicatedObjects/6/isSelected",
                    "/floorplan/glbBase64",
                ],
                "summary": "床候选中心约为 (4.949, 9.370)m，落在由 kitchen 门窗和内墙名称推断的厨房围合区内；若它是有效摆放，会造成明显功能冲突。",
                "falsifiers": [
                    "deduplicatedObjects/6 只是未启用的候选预览。",
                    "家居坐标与嵌入式 GLB 使用不同且尚未记录的坐标变换。",
                    "kitchen 节点命名与实际空间用途不一致。",
                ],
            },
            {
                "id": "issue-bookshelf-mirror-overlap",
                "priority": "P2 moderate",
                "status": "inferred",
                "confidence": 0.76,
                "method": "physical",
                "evidenceRefs": [
                    "/deduplicatedObjects/7/transform",
                    "/deduplicatedObjects/7/estimatedDimensions",
                    "/deduplicatedObjects/8/transform",
                    "/deduplicatedObjects/8/estimatedDimensions",
                ],
                "summary": "书架与镜子中心相距约 0.23m；若占地接近当前未实测估值，两者会严重重叠或无法正常使用。",
                "falsifiers": [
                    "实际模型占地远小于占位尺寸。",
                    "镜子是安装在书架表面的附属件而非独立落地物。",
                    "两件候选不会同时启用。",
                ],
            },
            {
                "id": "issue-bedroom-window-clearance",
                "priority": "P2 moderate",
                "status": "inferred",
                "confidence": 0.72,
                "method": "form",
                "evidenceRefs": [
                    "/deduplicatedObjects/7/transform/position",
                    "/deduplicatedObjects/8/transform/position",
                    "/floorplan/glbBase64",
                ],
                "summary": "书架和镜子都靠近 bedroom A 的连续窗墙，可能影响采光、窗扇/窗帘使用和清洁维护。",
                "falsifiers": [
                    "窗为固定窗且家具高度低于窗台。",
                    "实际占地、高度或坐标变换与当前记录不同。",
                ],
            },
            {
                "id": "issue-table-lamp-support-unknown",
                "priority": "P2 moderate",
                "status": "observed",
                "confidence": 0.9,
                "method": "physical",
                "evidenceRefs": [
                    "/deduplicatedObjects/0/name",
                    "/deduplicatedObjects/0/transform/position",
                    "/deduplicatedObjects/0/estimatedDimensions",
                ],
                "summary": "台灯作为独立对象记录，但没有 supportSurfaceId、电线走向或稳定承载面的信息；它又接近入口一侧，需先排除绊倒和倾倒风险。",
                "falsifiers": ["现场已有稳定边几/玄关柜承载，且电线完全离开门扇与通道。"],
            },
            {
                "id": "issue-mirror-bed-relation-unknown",
                "priority": "P3 optional",
                "status": "unknown",
                "confidence": 0.45,
                "method": "form",
                "evidenceRefs": [
                    "/deduplicatedObjects/8/transform/rotation",
                    "/deduplicatedObjects/8/isSelected",
                    "/deduplicatedObjects/6/transform/position",
                ],
                "summary": "镜子已被选中，但 JSON 不能证明其反射面朝向，也不能确认是否照床或造成夜间眩光。",
                "falsifiers": ["现场视线检查确认镜子不反射床、门口强光或高频座位。"],
            },
        ],
        "recommendations": [
            {
                "id": "rec-normalize-layout-first",
                "issueIds": ["issue-schema-not-validatable"],
                "state": "recommended",
                "actionClass": "repair",
                "action": "先把 GLB 中的房间、门窗和固定设施映射为 rooms；把启用的 candidate 对象映射为 furniture，并补齐真实占地、可移动性和门窗开启区。",
                "reason": "这是后续判断越界、重叠、通道和任何坐标调整的硬前提。",
                "cost": "none-to-low",
                "effort": "medium",
                "reversibility": "high",
                "confidence": 1.0,
                "jsonRefs": ["/floorplan", "/deduplicatedObjects"],
                "verification": "重新运行 validate_layout.py，要求 rooms/furniture 不再缺失，且 validation.valid 为 true。",
            },
            {
                "id": "rec-confirm-bed-candidate",
                "issueIds": ["issue-bed-in-kitchen-semantic-zone"],
                "state": "recommended",
                "actionClass": "clear",
                "action": "先确认 bed 候选是否属于有效布局；若只是预览，将其从启用列表中剔除。若确实要使用，改放到真实卧室后再做完整校验，不在当前文件里直接改坐标。",
                "reason": "床与厨房的功能冲突比任何象征方位都更应优先处理；当前置信度和几何完整度不足以自动大搬。",
                "cost": "none",
                "effort": "low-to-medium",
                "reversibility": "high",
                "confidence": 0.82,
                "jsonRefs": ["/deduplicatedObjects/6"],
                "verification": "确认 candidate 生命周期；启用时床占地必须完全位于 bedroom，多侧可达且不侵入门扇和主通道。",
            },
            {
                "id": "rec-separate-bookshelf-mirror",
                "issueIds": [
                    "issue-bookshelf-mirror-overlap",
                    "issue-bedroom-window-clearance",
                ],
                "state": "recommended",
                "actionClass": "redirect",
                "action": "不要同时保留书架和落地镜在当前点位。优先把书架贴实体墙布置，并让镜子避开窗扇、窗帘和高频通道；具体坐标待实测尺寸后确定。",
                "reason": "先解决潜在重叠和窗墙维护，再谈“有靠”与视觉稳定。",
                "cost": "none",
                "effort": "low",
                "reversibility": "high",
                "confidence": 0.76,
                "jsonRefs": ["/deduplicatedObjects/7", "/deduplicatedObjects/8"],
                "verification": "两件物品边界不重叠；窗帘和窗扇可用；书架固定防倾倒；主通道净宽不低于 0.80m。",
            },
            {
                "id": "rec-stabilize-entry-light",
                "issueIds": ["issue-table-lamp-support-unknown"],
                "state": "recommended",
                "actionClass": "stabilize",
                "action": "入口附近可以保留柔和照明，但台灯必须放在稳定承载面上，电线沿墙固定并完全离开门扇和步行线；没有边几时先不要落位。",
                "reason": "这同时改善入口辨识和传统所说的“明堂清晰”，且不增加屏风或植物占地。",
                "cost": "none-to-low",
                "effort": "low",
                "reversibility": "high",
                "confidence": 0.9,
                "jsonRefs": ["/deduplicatedObjects/0"],
                "verification": "开门、夜间行走和清扫均不碰线；灯具稳定、不眩光、与可燃物保持安全距离。",
            },
            {
                "id": "rec-check-mirror-reflection",
                "issueIds": ["issue-mirror-bed-relation-unknown"],
                "state": "recommended",
                "actionClass": "redirect",
                "action": "夜间从床位和房门处做一次视线检查；若镜面直接反射床或入口强光，只需微转镜面或夜间加可移除遮布。",
                "reason": "处理的是反光、突然映像和睡眠干扰，不把镜子当作万能化解物。",
                "cost": "none",
                "effort": "low",
                "reversibility": "high",
                "confidence": 0.45,
                "jsonRefs": ["/deduplicatedObjects/8"],
                "verification": "连续 7 晚观察夜间眩光、起夜惊扰和睡眠感受是否改善。",
            },
        ],
        "timeAdjustment": None,
        "catalogFurnitureRecommendations": [],
        "catalogStatus": "catalog_not_configured",
        "catalogNote": "输入未指定 meta.furnitureCatalogPath，项目默认 backend/sample_data/furniture/catalog.json 不存在，因此未编造商品推荐。",
        "appliedChanges": [],
        "proposedMajorFurniturePlan": [],
        "rejectedCandidates": [
            {
                "id": "candidate-auto-move-bed",
                "state": "rejected",
                "action": "自动把床移动到卧室",
                "reason": "缺少标准房间多边形、真实床尺寸、门扇开启区和可移动性，且跨功能区移动属于家具大改。",
                "fallback": "先确认对象是否启用并完成结构化映射。",
            },
            {
                "id": "candidate-add-entry-screen-or-plant",
                "state": "rejected",
                "action": "在入口新增屏风或植物",
                "reason": "入口门扇与连续通道尚未验证，新增落地物可能缩窄通行。",
                "fallback": "只保留清理和安全照明建议。",
            },
        ],
        "jsonPatch": [],
        "validation": {
            "valid": False,
            "errors": [
                {"code": "rooms.missing", "message": "rooms must be an array"},
                {"code": "furniture.missing", "message": "furniture must be an array"},
            ],
            "warnings": [
                {
                    "code": "meta.units-missing",
                    "message": "标准 meta.units 缺失；已从 /floorplan/room/unit 映射到 m，但校验器不识别该自定义路径。",
                },
                {
                    "code": "circulation.not-proven",
                    "message": "continuous egress and passage width were not proven",
                },
            ],
            "validator": "validate_layout.py",
            "scope": [
                "JSON parsing",
                "required standard arrays",
                "room references",
                "floor footprint containment",
                "convex overlap",
                "provided opening clearance polygons",
            ],
            "note": "按照 skill 边界，验证失败时仅回写分析，不修改任何实体坐标。",
        },
    }

    data["fengshuiAnalysis"] = analysis
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    with args.output.open("r", encoding="utf-8") as handle:
        reparsed = json.load(handle)

    assert reparsed["sceneId"] == original["sceneId"]
    assert reparsed["floorplan"]["glbBase64"] == original["floorplan"]["glbBase64"]
    assert reparsed["deduplicatedObjects"] == original["deduplicatedObjects"]
    assert "fengshuiAnalysis" in reparsed


if __name__ == "__main__":
    main()
