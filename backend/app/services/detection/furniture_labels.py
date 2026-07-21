FURNITURE_LABELS_ZH = {
    "sofa": "沙发",
    "bed": "床",
    "chair": "椅子",
    "armchair": "单人椅",
    "table": "桌子",
    "coffee table": "茶几",
    "dining table": "餐桌",
    "desk": "书桌",
    "cabinet": "柜子",
    "wardrobe": "衣柜",
    "tv stand": "电视柜",
    "bookshelf": "书架",
    "nightstand": "床头柜",
    "chandelier": "吊灯",
    "pendant light": "吊灯",
    "floor lamp": "落地灯",
    "table lamp": "台灯",
    "rug": "地毯",
    "curtain": "窗帘",
    "plant": "绿植",
    "mirror": "镜子",
    "painting": "装饰画",
    "vase": "花瓶",
}


def normalize_label(label: str) -> str:
    normalized = label.strip().lower().replace("_", " ")
    return " ".join(normalized.split())


def label_to_zh(label: str) -> str:
    normalized = normalize_label(label)
    return FURNITURE_LABELS_ZH.get(normalized, label.strip())
