import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.vision_semantics.label_policy import filter_semantic_labels, to_grounding_prompt


def main() -> None:
    raw = [
        {"label": "dining_table", "name": "餐桌"},
        {"label": "coffee table", "name": "茶几"},
        {"label": "food", "name": "食物"},
        {"label": "pendant-light", "name": "吊灯"},
        {"label": "book", "name": "书"},
    ]
    filtered = filter_semantic_labels(raw)
    print("filtered:", filtered)
    print("prompt:", to_grounding_prompt([item["label"] for item in filtered]))


if __name__ == "__main__":
    main()
