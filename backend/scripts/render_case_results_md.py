import json
from pathlib import Path

payload = json.loads(Path("docs/spatial_agent_case_results.json").read_text(encoding="utf-8"))
fence = chr(96) * 3
lines: list[str] = []
a = lines.append
a("# Spatial Check 多 Agent 案例效果")
a("")
a(f"- 生成时间：{payload['generatedAt']}")
a(f"- Provider：`{payload['provider']}`")
a(f"- Model：`{payload['model']}`")
a(f"- Base URL：`{payload['baseUrl']}`")
a("- 场景：客餐厅综合场景（12 家具 + 2门2窗）")
a("")
a("> 下列输出为真实 LLM（GLM-4-Flash）跑出的完整结果：几何 checks + 多 Agent agentReport。")
a("")

for item in payload["cases"]:
    a(f"## {item.get('title', item.get('id'))}")
    a("")
    if "error" in item:
        a(f"**运行失败**：{item['error']}")
        a("")
        continue
    a(f"**目的**：{item['goal']}")
    a(f"**耗时**：{item['elapsedSec']}s")
    a("")
    a("### 候选家具")
    a(f"{fence}json")
    a(json.dumps(item["request"]["candidate"], ensure_ascii=False, indent=2))
    a(fence)
    a("")
    a("### 用户画像")
    a(f"{fence}json")
    a(json.dumps(item["request"]["userProfile"], ensure_ascii=False, indent=2))
    a(fence)
    a("")
    a("### 几何检测结果")
    a(f"- overallStatus: `{item['geometry']['overallStatus']}`")
    a(f"- feedback: {item['geometry']['feedback']}")
    a("")
    a(f"{fence}json")
    a(json.dumps(item["geometry"]["checks"], ensure_ascii=False, indent=2))
    a(fence)
    a("")
    ar = item["agentReport"]
    a("### Agent 汇总报告")
    a(f"- score: **{ar['score']}**")
    a(f"- scoreDimensions: `{json.dumps(ar['scoreDimensions'], ensure_ascii=False)}`")
    a(f"- summary: {ar['summary']}")
    a("")
    a("**highlights**")
    for h in ar.get("highlights") or []:
        a(f"- {h}")
    a("")
    a("**Top suggestions**")
    a("")
    a(f"{fence}json")
    a(json.dumps(ar.get("suggestions") or [], ensure_ascii=False, indent=2))
    a(fence)
    a("")
    a("**agentOutputs（Layout / Lifestyle 原始输出）**")
    a("")
    a(f"{fence}json")
    a(json.dumps(ar.get("agentOutputs") or [], ensure_ascii=False, indent=2))
    a(fence)
    a("")
    a("---")
    a("")

scene = payload["cases"][0]["request"]["sceneSummary"]
a("## 场景门窗与家具清单（共用）")
a("")
a(f"{fence}json")
a(
    json.dumps(
        {
            "sceneId": scene["sceneId"],
            "room": scene["room"],
            "openings": scene["openings"],
            "objects": scene["objects"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
a(fence)
a("")

Path("docs/spatial_agent_case_results.md").write_text("\n".join(lines), encoding="utf-8")
print("ok", len(lines))
