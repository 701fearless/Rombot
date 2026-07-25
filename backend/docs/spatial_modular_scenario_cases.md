# 模块化布局 + 场景化建议 案例效果

- 生成时间：2026-07-25T00:26:28
- Provider：`ark`
- Model：`GLM-4-Flash`
- Base URL：`https://llmapi.paratera.com`
- LLM live：`True`
- Phase1：`layout.moves` + `layout.advices` + `scenarioOptions`
- Phase2：`/api/room/scenario-advice` 按场景返回修改建议

## 模式说明（两套 API）

- 单家具摆放：`POST /api/room/placement-check`（旧 `/spatial-check` 兼容）
- 全屋布局：`POST /api/room/room-layout`
- 场景深化：`POST /api/room/scenario-advice`（`mode=placement|room`）

文档追加全屋案例时间：2026-07-25T00:41:47；provider=`mock`；live=`False`

## 可选场景

- `elder` 养老：面向家中有老人的适老化布局优化。
- `infant` 育婴：面向有婴幼儿/儿童的安全与活动区优化。
- `pet` 养宠：面向养猫/狗等宠物的活动与通行优化。
- `fengshui` 风水：在不改建前提下的舒适风水布置建议。

## 案例1：落地书架堵住阳台门

### 耗时

- Phase1（几何 + 布局模块）：**18.296s**
- Phase2（场景建议）：**26.573s**
- 合计：**44.869s**

### 输入（Phase1 `POST /api/room/spatial-check`）

```json
{
  "enableAgents": true,
  "candidate": {
    "id": "candidate_bookshelf",
    "label": "bookshelf",
    "name": "落地书架",
    "position": [
      4.7,
      0.0,
      4.25
    ],
    "rotation": [
      0.0,
      0.0,
      0.0
    ],
    "size": [
      1.0,
      2.0,
      0.35
    ]
  },
  "userProfile": {
    "familyMembers": [
      "adult",
      "adult",
      "child",
      "elderly"
    ],
    "hasChildren": true,
    "hasElderly": true,
    "pets": [
      "cat",
      "dog"
    ],
    "dailyHabits": [
      "remote_work",
      "evening_tv",
      "family_dinner",
      "reading"
    ],
    "storageHabits": "books_and_toys_need_dedicated_zones",
    "fengShuiPreference": true,
    "preferPrivacy": true,
    "preferComfort": true
  },
  "scene": {
    "sceneId": "rich_family_living_dining",
    "unit": "meter",
    "room": {
      "width": 5.6,
      "depth": 4.8,
      "height": 2.8
    },
    "objectCount": 12,
    "objects": [
      {
        "id": "sofa_1",
        "name": "三人沙发",
        "label": "sofa",
        "position": [
          2.0,
          0.0,
          3.9
        ],
        "size": [
          2.2,
          0.9,
          0.9
        ]
      },
      {
        "id": "armchair_1",
        "name": "单人椅",
        "label": "armchair",
        "position": [
          3.7,
          0.0,
          3.5
        ],
        "size": [
          0.75,
          0.9,
          0.75
        ]
      },
      {
        "id": "coffee_table_1",
        "name": "茶几",
        "label": "coffee_table",
        "position": [
          2.1,
          0.0,
          2.85
        ],
        "size": [
          1.1,
          0.45,
          0.55
        ]
      },
      {
        "id": "rug_1",
        "name": "客厅地毯",
        "label": "rug",
        "position": [
          2.2,
          0.01,
          3.1
        ],
        "size": [
          2.8,
          0.02,
          2.0
        ]
      },
      {
        "id": "tv_stand_1",
        "name": "电视柜",
        "label": "tv_stand",
        "position": [
          2.0,
          0.0,
          0.4
        ],
        "size": [
          1.8,
          0.5,
          0.4
        ]
      },
      {
        "id": "sideboard_1",
        "name": "边柜",
        "label": "cabinet",
        "position": [
          5.15,
          0.0,
          1.6
        ],
        "size": [
          0.45,
          0.85,
          1.4
        ]
      },
      {
        "id": "dining_table_1",
        "name": "餐桌",
        "label": "dining_table",
        "position": [
          4.3,
          0.0,
          2.6
        ],
        "size": [
          1.4,
          0.75,
          0.9
        ]
      },
      {
        "id": "chair_1",
        "name": "餐椅A",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          2.0
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "chair_2",
        "name": "餐椅B",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          3.2
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "desk_1",
        "name": "书桌",
        "label": "desk",
        "position": [
          0.7,
          0.0,
          2.2
        ],
        "size": [
          1.2,
          0.75,
          0.6
        ]
      },
      {
        "id": "plant_1",
        "name": "绿植",
        "label": "plant",
        "position": [
          0.45,
          0.0,
          4.35
        ],
        "size": [
          0.4,
          1.2,
          0.4
        ]
      },
      {
        "id": "floor_lamp_1",
        "name": "落地灯",
        "label": "floor_lamp",
        "position": [
          3.55,
          0.0,
          4.35
        ],
        "size": [
          0.35,
          1.7,
          0.35
        ]
      }
    ],
    "openings": [
      {
        "id": "door_main",
        "type": "door",
        "name": "入户门",
        "position": [
          0.7,
          1.05,
          0.0
        ],
        "rotation": [
          0.0,
          0.0,
          0.0
        ],
        "size": [
          1.0,
          2.1,
          0.12
        ],
        "clearanceDepth": 1.0
      },
      {
        "id": "door_balcony",
        "type": "door",
        "name": "阳台门",
        "position": [
          5.0,
          1.05,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          0.9,
          2.1,
          0.12
        ],
        "clearanceDepth": 0.9
      },
      {
        "id": "window_living",
        "type": "window",
        "name": "客厅落地窗",
        "position": [
          2.4,
          1.2,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          2.4,
          2.0,
          0.12
        ],
        "clearanceDepth": 0.4
      },
      {
        "id": "window_side",
        "type": "window",
        "name": "侧窗",
        "position": [
          5.6,
          1.4,
          3.2
        ],
        "rotation": [
          0.0,
          -90.0,
          0.0
        ],
        "size": [
          1.2,
          1.2,
          0.12
        ],
        "clearanceDepth": 0.35
      }
    ]
  }
}
```
### 输入（Phase2 `POST /api/room/scenario-advice`）

```json
{
  "scenarios": [
    "elder",
    "pet",
    "fengshui"
  ],
  "candidate": {
    "id": "candidate_bookshelf",
    "label": "bookshelf",
    "name": "落地书架",
    "position": [
      4.7,
      0.0,
      4.25
    ],
    "rotation": [
      0.0,
      0.0,
      0.0
    ],
    "size": [
      1.0,
      2.0,
      0.35
    ]
  },
  "userProfile": {
    "familyMembers": [
      "adult",
      "adult",
      "child",
      "elderly"
    ],
    "hasChildren": true,
    "hasElderly": true,
    "pets": [
      "cat",
      "dog"
    ],
    "dailyHabits": [
      "remote_work",
      "evening_tv",
      "family_dinner",
      "reading"
    ],
    "storageHabits": "books_and_toys_need_dedicated_zones",
    "fengShuiPreference": true,
    "preferPrivacy": true,
    "preferComfort": true
  },
  "geometryChecks": [
    {
      "ruleId": "fit",
      "name": "空间适配",
      "status": "pass",
      "message": "家具可正常放置",
      "suggestion": null,
      "details": {
        "withinRoom": true,
        "overflow_m": {
          "left": 0.0,
          "right": 0.0,
          "back": 0.0,
          "front": 0.0
        }
      }
    },
    {
      "ruleId": "collision",
      "name": "家具冲突",
      "status": "pass",
      "message": "未与其他家具发生重叠",
      "suggestion": null,
      "details": {
        "conflicts": []
      }
    },
    {
      "ruleId": "accessibility",
      "name": "门窗可达性",
      "status": "fail",
      "message": "进入阳台门开启区域",
      "suggestion": "该位置会影响房门正常开启，建议远离门口区域。",
      "details": {
        "blocked": [
          {
            "openingId": "door_balcony",
            "type": "door",
            "name": "阳台门"
          }
        ]
      }
    },
    {
      "ruleId": "clearance",
      "name": "活动空间",
      "status": "pass",
      "message": "该家具类型暂无活动空间阈值，跳过检测",
      "suggestion": null,
      "details": {
        "sides": [],
        "skipped": true
      }
    }
  ],
  "layout": {
    "moves": [
      {
        "objectId": "candidate_bookshelf",
        "name": "落地书架",
        "fromPosition": [
          4.7,
          0.0,
          4.25
        ],
        "toPosition": [
          4.874,
          0.0,
          3.857
        ],
        "fromRotation": [
          0.0,
          0.0,
          0.0
        ],
        "toRotation": [
          0.0,
          0.0,
          0.0
        ],
        "reason": "离开阳台门净空区，建议移开约 43 cm",
        "source": "geometry"
      }
    ],
    "advices": [
      {
        "id": "layout_001",
        "priority": "高",
        "title": "优化阳台门通行空间",
        "problem": "阳台门开启区域被家具阻挡，影响通行。",
        "suggestion": "将落地书架移至距离阳台门约43cm的位置，确保门开启无阻。",
        "relatedObjectIds": [
          "candidate_bookshelf"
        ]
      },
      {
        "id": "layout_002",
        "priority": "中",
        "title": "调整沙发与电视柜间距",
        "problem": "沙发与电视柜之间距离过近，影响观看体验。",
        "suggestion": "将沙发向后移动约0.5米，增加与电视柜的距离，提升观看舒适度。",
        "relatedObjectIds": [
          "sofa_1",
          "tv_stand_1"
        ]
      },
      {
        "id": "layout_003",
        "priority": "中",
        "title": "优化餐桌与客厅家具布局",
        "problem": "餐桌附近空间拥挤，影响用餐舒适。",
        "suggestion": "将餐桌向客厅方向移动，与沙发保持一定距离，增加用餐空间。",
        "relatedObjectIds": [
          "dining_table_1",
          "sofa_1"
        ]
      },
      {
        "id": "layout_004",
        "priority": "低",
        "title": "调整落地灯位置",
        "problem": "落地灯位置影响客厅整体照明效果。",
        "suggestion": "将落地灯移至靠近沙发一侧，提供更均匀的照明。",
        "relatedObjectIds": [
          "floor_lamp_1"
        ]
      },
      {
        "id": "layout_005",
        "priority": "低",
        "title": "增加客厅与餐厅的视觉连接",
        "problem": "客厅与餐厅之间视觉连接不足。",
        "suggestion": "在客厅与餐厅之间放置一面装饰镜，增强空间视觉连接感。",
        "relatedObjectIds": [
          "rug_1",
          "coffee_table_1"
        ]
      }
    ],
    "summary": "空间布局需优化，确保通行无阻且家具摆放合理。"
  },
  "scene": {
    "sceneId": "rich_family_living_dining",
    "unit": "meter",
    "room": {
      "width": 5.6,
      "depth": 4.8,
      "height": 2.8
    },
    "objectCount": 12,
    "objects": [
      {
        "id": "sofa_1",
        "name": "三人沙发",
        "label": "sofa",
        "position": [
          2.0,
          0.0,
          3.9
        ],
        "size": [
          2.2,
          0.9,
          0.9
        ]
      },
      {
        "id": "armchair_1",
        "name": "单人椅",
        "label": "armchair",
        "position": [
          3.7,
          0.0,
          3.5
        ],
        "size": [
          0.75,
          0.9,
          0.75
        ]
      },
      {
        "id": "coffee_table_1",
        "name": "茶几",
        "label": "coffee_table",
        "position": [
          2.1,
          0.0,
          2.85
        ],
        "size": [
          1.1,
          0.45,
          0.55
        ]
      },
      {
        "id": "rug_1",
        "name": "客厅地毯",
        "label": "rug",
        "position": [
          2.2,
          0.01,
          3.1
        ],
        "size": [
          2.8,
          0.02,
          2.0
        ]
      },
      {
        "id": "tv_stand_1",
        "name": "电视柜",
        "label": "tv_stand",
        "position": [
          2.0,
          0.0,
          0.4
        ],
        "size": [
          1.8,
          0.5,
          0.4
        ]
      },
      {
        "id": "sideboard_1",
        "name": "边柜",
        "label": "cabinet",
        "position": [
          5.15,
          0.0,
          1.6
        ],
        "size": [
          0.45,
          0.85,
          1.4
        ]
      },
      {
        "id": "dining_table_1",
        "name": "餐桌",
        "label": "dining_table",
        "position": [
          4.3,
          0.0,
          2.6
        ],
        "size": [
          1.4,
          0.75,
          0.9
        ]
      },
      {
        "id": "chair_1",
        "name": "餐椅A",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          2.0
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "chair_2",
        "name": "餐椅B",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          3.2
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "desk_1",
        "name": "书桌",
        "label": "desk",
        "position": [
          0.7,
          0.0,
          2.2
        ],
        "size": [
          1.2,
          0.75,
          0.6
        ]
      },
      {
        "id": "plant_1",
        "name": "绿植",
        "label": "plant",
        "position": [
          0.45,
          0.0,
          4.35
        ],
        "size": [
          0.4,
          1.2,
          0.4
        ]
      },
      {
        "id": "floor_lamp_1",
        "name": "落地灯",
        "label": "floor_lamp",
        "position": [
          3.55,
          0.0,
          4.35
        ],
        "size": [
          0.35,
          1.7,
          0.35
        ]
      }
    ],
    "openings": [
      {
        "id": "door_main",
        "type": "door",
        "name": "入户门",
        "position": [
          0.7,
          1.05,
          0.0
        ],
        "rotation": [
          0.0,
          0.0,
          0.0
        ],
        "size": [
          1.0,
          2.1,
          0.12
        ],
        "clearanceDepth": 1.0
      },
      {
        "id": "door_balcony",
        "type": "door",
        "name": "阳台门",
        "position": [
          5.0,
          1.05,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          0.9,
          2.1,
          0.12
        ],
        "clearanceDepth": 0.9
      },
      {
        "id": "window_living",
        "type": "window",
        "name": "客厅落地窗",
        "position": [
          2.4,
          1.2,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          2.4,
          2.0,
          0.12
        ],
        "clearanceDepth": 0.4
      },
      {
        "id": "window_side",
        "type": "window",
        "name": "侧窗",
        "position": [
          5.6,
          1.4,
          3.2
        ],
        "rotation": [
          0.0,
          -90.0,
          0.0
        ],
        "size": [
          1.2,
          1.2,
          0.12
        ],
        "clearanceDepth": 0.35
      }
    ]
  }
}
```

### 输出摘要

- 几何 overallStatus：`fail`
- 布局 summary：空间布局需优化，确保通行无阻且家具摆放合理。
- 场景 summary：养老：针对老人居住的客厅空间，优化家具布局以提高安全性和舒适性。；养宠：优化宠物活动空间，确保安全与舒适。；风水：优化客厅风水布局，提升舒适度和视觉体验。

### 模块A：家具移动后的位置 `layout.moves`
```json
[
  {
    "objectId": "candidate_bookshelf",
    "name": "落地书架",
    "fromPosition": [
      4.7,
      0.0,
      4.25
    ],
    "toPosition": [
      4.874,
      0.0,
      3.857
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "离开阳台门净空区，建议移开约 43 cm",
    "source": "geometry"
  }
]
```

### 模块B：布局优化建议 `layout.advices`（中文）
```json
[
  {
    "id": "layout_001",
    "priority": "高",
    "title": "优化阳台门通行空间",
    "problem": "阳台门开启区域被家具阻挡，影响通行。",
    "suggestion": "将落地书架移至距离阳台门约43cm的位置，确保门开启无阻。",
    "relatedObjectIds": [
      "candidate_bookshelf"
    ]
  },
  {
    "id": "layout_002",
    "priority": "中",
    "title": "调整沙发与电视柜间距",
    "problem": "沙发与电视柜之间距离过近，影响观看体验。",
    "suggestion": "将沙发向后移动约0.5米，增加与电视柜的距离，提升观看舒适度。",
    "relatedObjectIds": [
      "sofa_1",
      "tv_stand_1"
    ]
  },
  {
    "id": "layout_003",
    "priority": "中",
    "title": "优化餐桌与客厅家具布局",
    "problem": "餐桌附近空间拥挤，影响用餐舒适。",
    "suggestion": "将餐桌向客厅方向移动，与沙发保持一定距离，增加用餐空间。",
    "relatedObjectIds": [
      "dining_table_1",
      "sofa_1"
    ]
  },
  {
    "id": "layout_004",
    "priority": "低",
    "title": "调整落地灯位置",
    "problem": "落地灯位置影响客厅整体照明效果。",
    "suggestion": "将落地灯移至靠近沙发一侧，提供更均匀的照明。",
    "relatedObjectIds": [
      "floor_lamp_1"
    ]
  },
  {
    "id": "layout_005",
    "priority": "低",
    "title": "增加客厅与餐厅的视觉连接",
    "problem": "客厅与餐厅之间视觉连接不足。",
    "suggestion": "在客厅与餐厅之间放置一面装饰镜，增强空间视觉连接感。",
    "relatedObjectIds": [
      "rug_1",
      "coffee_table_1"
    ]
  }
]
```

### 场景选择后的修改建议
- 已选场景：elder, pet, fengshui

```json
{
  "elder": [
    {
      "id": "elder_001",
      "scenarioId": "elder",
      "priority": "高",
      "title": "优化沙发位置，方便老人起身",
      "reason": "沙发位置靠近电视柜，起身时需要绕过电视柜，存在安全隐患。",
      "action": "将沙发向后移动约0.5米，使其靠近通道，方便老人起身。",
      "relatedObjectIds": [
        "sofa_1"
      ],
      "targetPosition": [
        2.0,
        0.0,
        4.4
      ]
    },
    {
      "id": "elder_002",
      "scenarioId": "elder",
      "priority": "中",
      "title": "调整餐桌位置，增加老人用餐空间",
      "reason": "餐桌位置靠近沙发，用餐时空间狭小，影响老人行动。",
      "action": "将餐桌向客厅方向移动，与沙发保持一定距离，增加用餐空间。",
      "relatedObjectIds": [
        "dining_table_1",
        "sofa_1"
      ],
      "targetPosition": [
        4.3,
        0.0,
        3.0
      ]
    },
    {
      "id": "elder_003",
      "scenarioId": "elder",
      "priority": "中",
      "title": "移除茶几，防止老人跌倒",
      "reason": "茶几位于沙发和电视柜之间，老人起身时容易绊倒。",
      "action": "移除茶几，确保老人起身净空。",
      "relatedObjectIds": [
        "coffee_table_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_004",
      "scenarioId": "elder",
      "priority": "低",
      "title": "调整落地灯位置，提供均匀照明",
      "reason": "落地灯位置影响客厅整体照明效果。",
      "action": "将落地灯移至靠近沙发一侧，提供更均匀的照明。",
      "relatedObjectIds": [
        "floor_lamp_1"
      ],
      "targetPosition": [
        3.55,
        0.0,
        3.35
      ]
    },
    {
      "id": "elder_005",
      "scenarioId": "elder",
      "priority": "低",
      "title": "增加扶手，保障老人安全",
      "reason": "客厅与餐厅之间缺乏扶手，老人行走时容易跌倒。",
      "action": "在客厅与餐厅之间安装扶手，保障老人安全。",
      "relatedObjectIds": [],
      "targetPosition": null
    }
  ],
  "pet": [
    {
      "id": "pet_001",
      "scenarioId": "pet",
      "priority": "高",
      "title": "设置宠物活动区",
      "reason": "宠物需要一个专门的区域进行活动。",
      "action": "在客厅地毯附近设置一个宠物活动区，留出足够的空间供宠物奔跑和玩耍。",
      "relatedObjectIds": [
        "rug_1"
      ],
      "targetPosition": null
    },
    {
      "id": "pet_002",
      "scenarioId": "pet",
      "priority": "中",
      "title": "优化宠物通道",
      "reason": "宠物通道需要宽敞，避免绊倒。",
      "action": "确保宠物通道无障碍物，特别是在沙发和茶几之间。",
      "relatedObjectIds": [
        "sofa_1",
        "coffee_table_1"
      ],
      "targetPosition": null
    },
    {
      "id": "pet_003",
      "scenarioId": "pet",
      "priority": "中",
      "title": "避免门摆阻挡",
      "reason": "门摆可能会阻挡宠物进出。",
      "action": "在门附近留出足够的空间，确保宠物可以自由进出。",
      "relatedObjectIds": [
        "door_main",
        "door_balcony"
      ],
      "targetPosition": null
    },
    {
      "id": "pet_004",
      "scenarioId": "pet",
      "priority": "低",
      "title": "留出进食/休息角落",
      "reason": "宠物需要一个安静的地方进食和休息。",
      "action": "在客厅的一角放置宠物食盆和床，供宠物使用。",
      "relatedObjectIds": [],
      "targetPosition": null
    },
    {
      "id": "pet_005",
      "scenarioId": "pet",
      "priority": "低",
      "title": "考虑宠物视线高度",
      "reason": "宠物需要在其视线高度范围内活动。",
      "action": "确保家具摆放不会阻挡宠物视线，特别是在窗边活动区。",
      "relatedObjectIds": [
        "window_living",
        "window_side"
      ],
      "targetPosition": null
    }
  ],
  "fengshui": [
    {
      "id": "fengshui_001",
      "scenarioId": "fengshui",
      "priority": "高",
      "title": "调整沙发位置，避免门冲",
      "reason": "沙发正对入户门，形成门冲，影响风水。",
      "action": "将沙发位置调整至不直接面对入户门的位置。",
      "relatedObjectIds": [
        "sofa_1",
        "door_main"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_002",
      "scenarioId": "fengshui",
      "priority": "中",
      "title": "优化餐桌布局，增加用餐空间",
      "reason": "餐桌附近空间拥挤，影响用餐舒适。",
      "action": "将餐桌向客厅方向移动，与沙发保持一定距离。",
      "relatedObjectIds": [
        "dining_table_1",
        "sofa_1"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_003",
      "scenarioId": "fengshui",
      "priority": "中",
      "title": "调整落地灯位置，提供均匀照明",
      "reason": "落地灯位置影响客厅整体照明效果。",
      "action": "将落地灯移至靠近沙发一侧，提供更均匀的照明。",
      "relatedObjectIds": [
        "floor_lamp_1"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_004",
      "scenarioId": "fengshui",
      "priority": "低",
      "title": "增加绿植，改善室内环境",
      "reason": "室内绿植较少，不利于风水。",
      "action": "在客厅适当位置增加绿植，如植物角或窗台。",
      "relatedObjectIds": [
        "plant_1"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_005",
      "scenarioId": "fengshui",
      "priority": "低",
      "title": "优化电视柜位置，避免直对窗户",
      "reason": "电视柜正对窗户，影响电视观看效果。",
      "action": "将电视柜位置调整至不直接面对窗户的位置。",
      "relatedObjectIds": [
        "tv_stand_1",
        "window_living"
      ],
      "targetPosition": null
    }
  ]
}
```

---

## 案例2：新沙发压到茶几区

### 耗时

- Phase1（几何 + 布局模块）：**21.494s**
- Phase2（场景建议）：**21.218s**
- 合计：**42.713s**

### 输入（Phase1 `POST /api/room/spatial-check`）

```json
{
  "enableAgents": true,
  "candidate": {
    "id": "candidate_sofa_new",
    "label": "sofa",
    "name": "新沙发",
    "position": [
      2.1,
      0.0,
      2.9
    ],
    "rotation": [
      0.0,
      0.0,
      0.0
    ],
    "size": [
      2.2,
      0.9,
      0.9
    ]
  },
  "userProfile": {
    "familyMembers": [
      "adult",
      "adult",
      "child",
      "elderly"
    ],
    "hasChildren": true,
    "hasElderly": true,
    "pets": [
      "cat",
      "dog"
    ],
    "dailyHabits": [
      "remote_work",
      "evening_tv",
      "family_dinner",
      "reading"
    ],
    "storageHabits": "books_and_toys_need_dedicated_zones",
    "fengShuiPreference": true,
    "preferPrivacy": true,
    "preferComfort": true
  },
  "scene": {
    "sceneId": "rich_family_living_dining",
    "unit": "meter",
    "room": {
      "width": 5.6,
      "depth": 4.8,
      "height": 2.8
    },
    "objectCount": 12,
    "objects": [
      {
        "id": "sofa_1",
        "name": "三人沙发",
        "label": "sofa",
        "position": [
          2.0,
          0.0,
          3.9
        ],
        "size": [
          2.2,
          0.9,
          0.9
        ]
      },
      {
        "id": "armchair_1",
        "name": "单人椅",
        "label": "armchair",
        "position": [
          3.7,
          0.0,
          3.5
        ],
        "size": [
          0.75,
          0.9,
          0.75
        ]
      },
      {
        "id": "coffee_table_1",
        "name": "茶几",
        "label": "coffee_table",
        "position": [
          2.1,
          0.0,
          2.85
        ],
        "size": [
          1.1,
          0.45,
          0.55
        ]
      },
      {
        "id": "rug_1",
        "name": "客厅地毯",
        "label": "rug",
        "position": [
          2.2,
          0.01,
          3.1
        ],
        "size": [
          2.8,
          0.02,
          2.0
        ]
      },
      {
        "id": "tv_stand_1",
        "name": "电视柜",
        "label": "tv_stand",
        "position": [
          2.0,
          0.0,
          0.4
        ],
        "size": [
          1.8,
          0.5,
          0.4
        ]
      },
      {
        "id": "sideboard_1",
        "name": "边柜",
        "label": "cabinet",
        "position": [
          5.15,
          0.0,
          1.6
        ],
        "size": [
          0.45,
          0.85,
          1.4
        ]
      },
      {
        "id": "dining_table_1",
        "name": "餐桌",
        "label": "dining_table",
        "position": [
          4.3,
          0.0,
          2.6
        ],
        "size": [
          1.4,
          0.75,
          0.9
        ]
      },
      {
        "id": "chair_1",
        "name": "餐椅A",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          2.0
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "chair_2",
        "name": "餐椅B",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          3.2
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "desk_1",
        "name": "书桌",
        "label": "desk",
        "position": [
          0.7,
          0.0,
          2.2
        ],
        "size": [
          1.2,
          0.75,
          0.6
        ]
      },
      {
        "id": "plant_1",
        "name": "绿植",
        "label": "plant",
        "position": [
          0.45,
          0.0,
          4.35
        ],
        "size": [
          0.4,
          1.2,
          0.4
        ]
      },
      {
        "id": "floor_lamp_1",
        "name": "落地灯",
        "label": "floor_lamp",
        "position": [
          3.55,
          0.0,
          4.35
        ],
        "size": [
          0.35,
          1.7,
          0.35
        ]
      }
    ],
    "openings": [
      {
        "id": "door_main",
        "type": "door",
        "name": "入户门",
        "position": [
          0.7,
          1.05,
          0.0
        ],
        "rotation": [
          0.0,
          0.0,
          0.0
        ],
        "size": [
          1.0,
          2.1,
          0.12
        ],
        "clearanceDepth": 1.0
      },
      {
        "id": "door_balcony",
        "type": "door",
        "name": "阳台门",
        "position": [
          5.0,
          1.05,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          0.9,
          2.1,
          0.12
        ],
        "clearanceDepth": 0.9
      },
      {
        "id": "window_living",
        "type": "window",
        "name": "客厅落地窗",
        "position": [
          2.4,
          1.2,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          2.4,
          2.0,
          0.12
        ],
        "clearanceDepth": 0.4
      },
      {
        "id": "window_side",
        "type": "window",
        "name": "侧窗",
        "position": [
          5.6,
          1.4,
          3.2
        ],
        "rotation": [
          0.0,
          -90.0,
          0.0
        ],
        "size": [
          1.2,
          1.2,
          0.12
        ],
        "clearanceDepth": 0.35
      }
    ]
  }
}
```

### 输入（Phase2 `POST /api/room/scenario-advice`）

```json
{
  "scenarios": [
    "infant",
    "elder"
  ],
  "candidate": {
    "id": "candidate_sofa_new",
    "label": "sofa",
    "name": "新沙发",
    "position": [
      2.1,
      0.0,
      2.9
    ],
    "rotation": [
      0.0,
      0.0,
      0.0
    ],
    "size": [
      2.2,
      0.9,
      0.9
    ]
  },
  "userProfile": {
    "familyMembers": [
      "adult",
      "adult",
      "child",
      "elderly"
    ],
    "hasChildren": true,
    "hasElderly": true,
    "pets": [
      "cat",
      "dog"
    ],
    "dailyHabits": [
      "remote_work",
      "evening_tv",
      "family_dinner",
      "reading"
    ],
    "storageHabits": "books_and_toys_need_dedicated_zones",
    "fengShuiPreference": true,
    "preferPrivacy": true,
    "preferComfort": true
  },
  "geometryChecks": [
    {
      "ruleId": "fit",
      "name": "空间适配",
      "status": "pass",
      "message": "家具可正常放置",
      "suggestion": null,
      "details": {
        "withinRoom": true,
        "overflow_m": {
          "left": 0.0,
          "right": 0.0,
          "back": 0.0,
          "front": 0.0
        }
      }
    },
    {
      "ruleId": "collision",
      "name": "家具冲突",
      "status": "fail",
      "message": "与茶几、书桌发生重叠",
      "suggestion": "该家具与茶几、书桌发生重叠，请调整摆放位置（建议移开约 55 cm）。",
      "details": {
        "conflicts": [
          {
            "objectId": "coffee_table_1",
            "label": "coffee_table",
            "name": "茶几",
            "overlapDepth_m": 0.55
          },
          {
            "objectId": "desk_1",
            "label": "desk",
            "name": "书桌",
            "overlapDepth_m": 0.05
          }
        ]
      }
    },
    {
      "ruleId": "accessibility",
      "name": "门窗可达性",
      "status": "pass",
      "message": "不影响门窗使用",
      "suggestion": null,
      "details": {
        "blocked": []
      }
    },
    {
      "ruleId": "clearance",
      "name": "活动空间",
      "status": "warn",
      "message": "前方活动空间不足（0 cm，需 ≥ 60 cm）",
      "suggestion": "新沙发前方活动空间不足，建议向后移动约 60 cm。",
      "details": {
        "sides": [
          {
            "side": "front",
            "required_m": 0.6,
            "available_m": 0.0,
            "ok": false
          }
        ],
        "shortages": [
          {
            "side": "front",
            "required_m": 0.6,
            "available_m": 0.0,
            "ok": false
          }
        ]
      }
    }
  ],
  "layout": {
    "moves": [
      {
        "objectId": "candidate_sofa_new",
        "name": "新沙发",
        "fromPosition": [
          2.1,
          0.0,
          2.9
        ],
        "toPosition": [
          2.1,
          0.0,
          3.5
        ],
        "fromRotation": [
          0.0,
          0.0,
          0.0
        ],
        "toRotation": [
          0.0,
          0.0,
          0.0
        ],
        "reason": "与茶几、书桌重叠，建议分离约 60 cm",
        "source": "geometry"
      }
    ],
    "advices": [
      {
        "id": "layout_001",
        "priority": "高",
        "title": "调整新沙发位置",
        "problem": "新沙发与茶几、书桌发生重叠，且前方活动空间不足。",
        "suggestion": "将新沙发向后移动约 60 cm，避免与茶几、书桌重叠，并确保前方有足够的活动空间。",
        "relatedObjectIds": [
          "candidate_sofa_new"
        ]
      },
      {
        "id": "layout_002",
        "priority": "中",
        "title": "优化茶几位置",
        "problem": "茶几与书桌、新沙发存在重叠。",
        "suggestion": "将茶几向左侧移动约 55 cm，避免与书桌、新沙发重叠。",
        "relatedObjectIds": [
          "coffee_table_1"
        ]
      },
      {
        "id": "layout_003",
        "priority": "中",
        "title": "调整书桌位置",
        "problem": "书桌与新沙发存在重叠。",
        "suggestion": "将书桌向右侧移动约 5 cm，避免与新沙发重叠。",
        "relatedObjectIds": [
          "desk_1"
        ]
      },
      {
        "id": "layout_004",
        "priority": "低",
        "title": "优化绿植位置",
        "problem": "绿植位置较为孤立。",
        "suggestion": "将绿植放置在沙发与电视柜之间，增加空间的生机感。",
        "relatedObjectIds": [
          "plant_1"
        ]
      },
      {
        "id": "layout_005",
        "priority": "低",
        "title": "调整落地灯位置",
        "problem": "落地灯位置较为局促。",
        "suggestion": "将落地灯向右侧移动约 15 cm，增加使用空间。",
        "relatedObjectIds": [
          "floor_lamp_1"
        ]
      }
    ],
    "summary": "客厅家具摆放存在冲突和活动空间不足问题。"
  },
  "scene": {
    "sceneId": "rich_family_living_dining",
    "unit": "meter",
    "room": {
      "width": 5.6,
      "depth": 4.8,
      "height": 2.8
    },
    "objectCount": 12,
    "objects": [
      {
        "id": "sofa_1",
        "name": "三人沙发",
        "label": "sofa",
        "position": [
          2.0,
          0.0,
          3.9
        ],
        "size": [
          2.2,
          0.9,
          0.9
        ]
      },
      {
        "id": "armchair_1",
        "name": "单人椅",
        "label": "armchair",
        "position": [
          3.7,
          0.0,
          3.5
        ],
        "size": [
          0.75,
          0.9,
          0.75
        ]
      },
      {
        "id": "coffee_table_1",
        "name": "茶几",
        "label": "coffee_table",
        "position": [
          2.1,
          0.0,
          2.85
        ],
        "size": [
          1.1,
          0.45,
          0.55
        ]
      },
      {
        "id": "rug_1",
        "name": "客厅地毯",
        "label": "rug",
        "position": [
          2.2,
          0.01,
          3.1
        ],
        "size": [
          2.8,
          0.02,
          2.0
        ]
      },
      {
        "id": "tv_stand_1",
        "name": "电视柜",
        "label": "tv_stand",
        "position": [
          2.0,
          0.0,
          0.4
        ],
        "size": [
          1.8,
          0.5,
          0.4
        ]
      },
      {
        "id": "sideboard_1",
        "name": "边柜",
        "label": "cabinet",
        "position": [
          5.15,
          0.0,
          1.6
        ],
        "size": [
          0.45,
          0.85,
          1.4
        ]
      },
      {
        "id": "dining_table_1",
        "name": "餐桌",
        "label": "dining_table",
        "position": [
          4.3,
          0.0,
          2.6
        ],
        "size": [
          1.4,
          0.75,
          0.9
        ]
      },
      {
        "id": "chair_1",
        "name": "餐椅A",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          2.0
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "chair_2",
        "name": "餐椅B",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          3.2
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "desk_1",
        "name": "书桌",
        "label": "desk",
        "position": [
          0.7,
          0.0,
          2.2
        ],
        "size": [
          1.2,
          0.75,
          0.6
        ]
      },
      {
        "id": "plant_1",
        "name": "绿植",
        "label": "plant",
        "position": [
          0.45,
          0.0,
          4.35
        ],
        "size": [
          0.4,
          1.2,
          0.4
        ]
      },
      {
        "id": "floor_lamp_1",
        "name": "落地灯",
        "label": "floor_lamp",
        "position": [
          3.55,
          0.0,
          4.35
        ],
        "size": [
          0.35,
          1.7,
          0.35
        ]
      }
    ],
    "openings": [
      {
        "id": "door_main",
        "type": "door",
        "name": "入户门",
        "position": [
          0.7,
          1.05,
          0.0
        ],
        "rotation": [
          0.0,
          0.0,
          0.0
        ],
        "size": [
          1.0,
          2.1,
          0.12
        ],
        "clearanceDepth": 1.0
      },
      {
        "id": "door_balcony",
        "type": "door",
        "name": "阳台门",
        "position": [
          5.0,
          1.05,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          0.9,
          2.1,
          0.12
        ],
        "clearanceDepth": 0.9
      },
      {
        "id": "window_living",
        "type": "window",
        "name": "客厅落地窗",
        "position": [
          2.4,
          1.2,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          2.4,
          2.0,
          0.12
        ],
        "clearanceDepth": 0.4
      },
      {
        "id": "window_side",
        "type": "window",
        "name": "侧窗",
        "position": [
          5.6,
          1.4,
          3.2
        ],
        "rotation": [
          0.0,
          -90.0,
          0.0
        ],
        "size": [
          1.2,
          1.2,
          0.12
        ],
        "clearanceDepth": 0.35
      }
    ]
  }
}
```

### 输出摘要

- 几何 overallStatus：`fail`
- 布局 summary：客厅家具摆放存在冲突和活动空间不足问题。
- 场景 summary：育婴：本场景建议优化儿童活动区，确保安全并方便监护。；养老：客厅家具布局需优化以适应老人使用需求。

### 模块A：家具移动后的位置 `layout.moves`
```json
[
  {
    "objectId": "candidate_sofa_new",
    "name": "新沙发",
    "fromPosition": [
      2.1,
      0.0,
      2.9
    ],
    "toPosition": [
      2.1,
      0.0,
      3.5
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "与茶几、书桌重叠，建议分离约 60 cm",
    "source": "geometry"
  }
]
```

### 模块B：布局优化建议 `layout.advices`（中文）
```json
[
  {
    "id": "layout_001",
    "priority": "高",
    "title": "调整新沙发位置",
    "problem": "新沙发与茶几、书桌发生重叠，且前方活动空间不足。",
    "suggestion": "将新沙发向后移动约 60 cm，避免与茶几、书桌重叠，并确保前方有足够的活动空间。",
    "relatedObjectIds": [
      "candidate_sofa_new"
    ]
  },
  {
    "id": "layout_002",
    "priority": "中",
    "title": "优化茶几位置",
    "problem": "茶几与书桌、新沙发存在重叠。",
    "suggestion": "将茶几向左侧移动约 55 cm，避免与书桌、新沙发重叠。",
    "relatedObjectIds": [
      "coffee_table_1"
    ]
  },
  {
    "id": "layout_003",
    "priority": "中",
    "title": "调整书桌位置",
    "problem": "书桌与新沙发存在重叠。",
    "suggestion": "将书桌向右侧移动约 5 cm，避免与新沙发重叠。",
    "relatedObjectIds": [
      "desk_1"
    ]
  },
  {
    "id": "layout_004",
    "priority": "低",
    "title": "优化绿植位置",
    "problem": "绿植位置较为孤立。",
    "suggestion": "将绿植放置在沙发与电视柜之间，增加空间的生机感。",
    "relatedObjectIds": [
      "plant_1"
    ]
  },
  {
    "id": "layout_005",
    "priority": "低",
    "title": "调整落地灯位置",
    "problem": "落地灯位置较为局促。",
    "suggestion": "将落地灯向右侧移动约 15 cm，增加使用空间。",
    "relatedObjectIds": [
      "floor_lamp_1"
    ]
  }
]
```

### 场景选择后的修改建议
- 已选场景：infant, elder

```json
{
  "infant": [
    {
      "id": "infant_001",
      "scenarioId": "infant",
      "priority": "高",
      "title": "设置儿童活动区",
      "reason": "儿童需要安全的活动空间。",
      "action": "在客厅一角设置儿童活动区，使用柔软的地毯或防撞垫。",
      "relatedObjectIds": [],
      "targetPosition": null
    },
    {
      "id": "infant_002",
      "scenarioId": "infant",
      "priority": "中",
      "title": "移除锐角家具",
      "reason": "锐角家具可能造成儿童受伤。",
      "action": "将锐角家具如边柜、餐桌等移至儿童不可触及的地方。",
      "relatedObjectIds": [
        "sideboard_1",
        "dining_table_1"
      ],
      "targetPosition": null
    },
    {
      "id": "infant_003",
      "scenarioId": "infant",
      "priority": "中",
      "title": "确保通道安全",
      "reason": "通道需要足够宽敞，避免儿童跌倒。",
      "action": "确保通往阳台门和侧窗的通道至少有1米宽。",
      "relatedObjectIds": [],
      "targetPosition": null
    },
    {
      "id": "infant_004",
      "scenarioId": "infant",
      "priority": "低",
      "title": "玩具收纳整理",
      "reason": "玩具乱放可能造成儿童绊倒。",
      "action": "在儿童活动区附近设置玩具收纳箱，保持玩具整齐。",
      "relatedObjectIds": [],
      "targetPosition": null
    },
    {
      "id": "infant_005",
      "scenarioId": "infant",
      "priority": "低",
      "title": "监护视线无遮挡",
      "reason": "监护者需要随时观察儿童。",
      "action": "确保沙发和餐桌之间没有高大家具，避免遮挡监护视线。",
      "relatedObjectIds": [
        "sofa_1",
        "dining_table_1"
      ],
      "targetPosition": null
    }
  ],
  "elder": [
    {
      "id": "elder_001",
      "scenarioId": "elder",
      "priority": "高",
      "title": "调整新沙发位置",
      "reason": "新沙发位置影响老人起身净空和活动空间。",
      "action": "将新沙发向后移动约 60 cm，确保前方有足够的活动空间。",
      "relatedObjectIds": [
        "candidate_sofa_new"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_002",
      "scenarioId": "elder",
      "priority": "中",
      "title": "优化茶几位置",
      "reason": "茶几位置影响老人行走动线。",
      "action": "将茶几向左侧移动约 55 cm，避免与书桌、新沙发重叠。",
      "relatedObjectIds": [
        "coffee_table_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_003",
      "scenarioId": "elder",
      "priority": "中",
      "title": "调整书桌位置",
      "reason": "书桌位置影响老人行走动线。",
      "action": "将书桌向右侧移动约 5 cm，避免与新沙发重叠。",
      "relatedObjectIds": [
        "desk_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_004",
      "scenarioId": "elder",
      "priority": "低",
      "title": "优化绿植位置",
      "reason": "绿植位置较为孤立，不利于老人休息。",
      "action": "将绿植放置在沙发与电视柜之间，增加空间的生机感。",
      "relatedObjectIds": [
        "plant_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_005",
      "scenarioId": "elder",
      "priority": "低",
      "title": "调整落地灯位置",
      "reason": "落地灯位置影响老人使用。",
      "action": "将落地灯向右侧移动约 15 cm，增加使用空间。",
      "relatedObjectIds": [
        "floor_lamp_1"
      ],
      "targetPosition": null
    }
  ]
}
```

---

## 案例3：衣柜靠近入户门

### 耗时

- Phase1（几何 + 布局模块）：**17.141s**
- Phase2（场景建议）：**25.968s**
- 合计：**43.109s**

### 输入（Phase1 `POST /api/room/spatial-check`）

```json
{
  "enableAgents": true,
  "candidate": {
    "id": "candidate_wardrobe",
    "label": "wardrobe",
    "name": "衣柜",
    "position": [
      0.55,
      0.0,
      0.55
    ],
    "rotation": [
      0.0,
      0.0,
      0.0
    ],
    "size": [
      1.0,
      2.2,
      0.55
    ]
  },
  "userProfile": {
    "familyMembers": [
      "adult",
      "adult",
      "child",
      "elderly"
    ],
    "hasChildren": true,
    "hasElderly": true,
    "pets": [
      "cat",
      "dog"
    ],
    "dailyHabits": [
      "remote_work",
      "evening_tv",
      "family_dinner",
      "reading"
    ],
    "storageHabits": "books_and_toys_need_dedicated_zones",
    "fengShuiPreference": true,
    "preferPrivacy": true,
    "preferComfort": true
  },
  "scene": {
    "sceneId": "rich_family_living_dining",
    "unit": "meter",
    "room": {
      "width": 5.6,
      "depth": 4.8,
      "height": 2.8
    },
    "objectCount": 12,
    "objects": [
      {
        "id": "sofa_1",
        "name": "三人沙发",
        "label": "sofa",
        "position": [
          2.0,
          0.0,
          3.9
        ],
        "size": [
          2.2,
          0.9,
          0.9
        ]
      },
      {
        "id": "armchair_1",
        "name": "单人椅",
        "label": "armchair",
        "position": [
          3.7,
          0.0,
          3.5
        ],
        "size": [
          0.75,
          0.9,
          0.75
        ]
      },
      {
        "id": "coffee_table_1",
        "name": "茶几",
        "label": "coffee_table",
        "position": [
          2.1,
          0.0,
          2.85
        ],
        "size": [
          1.1,
          0.45,
          0.55
        ]
      },
      {
        "id": "rug_1",
        "name": "客厅地毯",
        "label": "rug",
        "position": [
          2.2,
          0.01,
          3.1
        ],
        "size": [
          2.8,
          0.02,
          2.0
        ]
      },
      {
        "id": "tv_stand_1",
        "name": "电视柜",
        "label": "tv_stand",
        "position": [
          2.0,
          0.0,
          0.4
        ],
        "size": [
          1.8,
          0.5,
          0.4
        ]
      },
      {
        "id": "sideboard_1",
        "name": "边柜",
        "label": "cabinet",
        "position": [
          5.15,
          0.0,
          1.6
        ],
        "size": [
          0.45,
          0.85,
          1.4
        ]
      },
      {
        "id": "dining_table_1",
        "name": "餐桌",
        "label": "dining_table",
        "position": [
          4.3,
          0.0,
          2.6
        ],
        "size": [
          1.4,
          0.75,
          0.9
        ]
      },
      {
        "id": "chair_1",
        "name": "餐椅A",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          2.0
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "chair_2",
        "name": "餐椅B",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          3.2
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "desk_1",
        "name": "书桌",
        "label": "desk",
        "position": [
          0.7,
          0.0,
          2.2
        ],
        "size": [
          1.2,
          0.75,
          0.6
        ]
      },
      {
        "id": "plant_1",
        "name": "绿植",
        "label": "plant",
        "position": [
          0.45,
          0.0,
          4.35
        ],
        "size": [
          0.4,
          1.2,
          0.4
        ]
      },
      {
        "id": "floor_lamp_1",
        "name": "落地灯",
        "label": "floor_lamp",
        "position": [
          3.55,
          0.0,
          4.35
        ],
        "size": [
          0.35,
          1.7,
          0.35
        ]
      }
    ],
    "openings": [
      {
        "id": "door_main",
        "type": "door",
        "name": "入户门",
        "position": [
          0.7,
          1.05,
          0.0
        ],
        "rotation": [
          0.0,
          0.0,
          0.0
        ],
        "size": [
          1.0,
          2.1,
          0.12
        ],
        "clearanceDepth": 1.0
      },
      {
        "id": "door_balcony",
        "type": "door",
        "name": "阳台门",
        "position": [
          5.0,
          1.05,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          0.9,
          2.1,
          0.12
        ],
        "clearanceDepth": 0.9
      },
      {
        "id": "window_living",
        "type": "window",
        "name": "客厅落地窗",
        "position": [
          2.4,
          1.2,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          2.4,
          2.0,
          0.12
        ],
        "clearanceDepth": 0.4
      },
      {
        "id": "window_side",
        "type": "window",
        "name": "侧窗",
        "position": [
          5.6,
          1.4,
          3.2
        ],
        "rotation": [
          0.0,
          -90.0,
          0.0
        ],
        "size": [
          1.2,
          1.2,
          0.12
        ],
        "clearanceDepth": 0.35
      }
    ]
  }
}
```

### 输入（Phase2 `POST /api/room/scenario-advice`）

```json
{
  "scenarios": [
    "fengshui",
    "pet",
    "elder"
  ],
  "candidate": {
    "id": "candidate_wardrobe",
    "label": "wardrobe",
    "name": "衣柜",
    "position": [
      0.55,
      0.0,
      0.55
    ],
    "rotation": [
      0.0,
      0.0,
      0.0
    ],
    "size": [
      1.0,
      2.2,
      0.55
    ]
  },
  "userProfile": {
    "familyMembers": [
      "adult",
      "adult",
      "child",
      "elderly"
    ],
    "hasChildren": true,
    "hasElderly": true,
    "pets": [
      "cat",
      "dog"
    ],
    "dailyHabits": [
      "remote_work",
      "evening_tv",
      "family_dinner",
      "reading"
    ],
    "storageHabits": "books_and_toys_need_dedicated_zones",
    "fengShuiPreference": true,
    "preferPrivacy": true,
    "preferComfort": true
  },
  "geometryChecks": [
    {
      "ruleId": "fit",
      "name": "空间适配",
      "status": "pass",
      "message": "家具可正常放置",
      "suggestion": null,
      "details": {
        "withinRoom": true,
        "overflow_m": {
          "left": 0.0,
          "right": 0.0,
          "back": 0.0,
          "front": 0.0
        }
      }
    },
    {
      "ruleId": "collision",
      "name": "家具冲突",
      "status": "pass",
      "message": "未与其他家具发生重叠",
      "suggestion": null,
      "details": {
        "conflicts": []
      }
    },
    {
      "ruleId": "accessibility",
      "name": "门窗可达性",
      "status": "fail",
      "message": "进入入户门开启区域",
      "suggestion": "该位置会影响房门正常开启，建议远离门口区域。",
      "details": {
        "blocked": [
          {
            "openingId": "door_main",
            "type": "door",
            "name": "入户门"
          }
        ]
      }
    },
    {
      "ruleId": "clearance",
      "name": "活动空间",
      "status": "warn",
      "message": "前方活动空间不足（25 cm，需 ≥ 60 cm）",
      "suggestion": "衣柜柜门开启空间不足，建议向后移动约 35 cm。",
      "details": {
        "sides": [
          {
            "side": "front",
            "required_m": 0.6,
            "available_m": 0.25,
            "ok": false
          }
        ],
        "shortages": [
          {
            "side": "front",
            "required_m": 0.6,
            "available_m": 0.25,
            "ok": false
          }
        ]
      }
    }
  ],
  "layout": {
    "moves": [
      {
        "objectId": "candidate_wardrobe",
        "name": "衣柜",
        "fromPosition": [
          0.55,
          0.0,
          0.55
        ],
        "toPosition": [
          0.5,
          0.0,
          0.508
        ],
        "fromRotation": [
          0.0,
          0.0,
          0.0
        ],
        "toRotation": [
          0.0,
          0.0,
          0.0
        ],
        "reason": "离开入户门净空区，建议移开约 63 cm",
        "source": "geometry"
      }
    ],
    "advices": [
      {
        "id": "layout_001",
        "priority": "高",
        "title": "调整衣柜位置",
        "problem": "衣柜位置影响入户门开启，且活动空间不足。",
        "suggestion": "将衣柜向后移动约35cm，避免与入户门冲突，并确保前方有足够的活动空间。",
        "relatedObjectIds": [
          "candidate_wardrobe"
        ]
      },
      {
        "id": "layout_002",
        "priority": "中",
        "title": "优化沙发布局",
        "problem": "沙发与电视柜之间距离过近，影响视线。",
        "suggestion": "将沙发向前移动约30cm，增加与电视柜之间的距离，改善视线。",
        "relatedObjectIds": [
          "sofa_1",
          "tv_stand_1"
        ]
      },
      {
        "id": "layout_003",
        "priority": "中",
        "title": "调整餐桌位置",
        "problem": "餐桌位置与沙发距离过近，影响客厅活动。",
        "suggestion": "将餐桌向后移动约50cm，增加与沙发的距离，提高客厅活动空间。",
        "relatedObjectIds": [
          "dining_table_1"
        ]
      },
      {
        "id": "layout_004",
        "priority": "低",
        "title": "优化茶几位置",
        "problem": "茶几位置靠近电视柜，可能影响电视柜使用。",
        "suggestion": "将茶几向沙发方向移动约20cm，避免与电视柜过于接近。",
        "relatedObjectIds": [
          "coffee_table_1"
        ]
      },
      {
        "id": "layout_005",
        "priority": "低",
        "title": "调整绿植位置",
        "problem": "绿植位置影响侧窗采光。",
        "suggestion": "将绿植向房间内部移动约30cm，避免遮挡侧窗采光。",
        "relatedObjectIds": [
          "plant_1"
        ]
      }
    ],
    "summary": "空间布局需优化，确保通行无阻且家具间距合理。"
  },
  "scene": {
    "sceneId": "rich_family_living_dining",
    "unit": "meter",
    "room": {
      "width": 5.6,
      "depth": 4.8,
      "height": 2.8
    },
    "objectCount": 12,
    "objects": [
      {
        "id": "sofa_1",
        "name": "三人沙发",
        "label": "sofa",
        "position": [
          2.0,
          0.0,
          3.9
        ],
        "size": [
          2.2,
          0.9,
          0.9
        ]
      },
      {
        "id": "armchair_1",
        "name": "单人椅",
        "label": "armchair",
        "position": [
          3.7,
          0.0,
          3.5
        ],
        "size": [
          0.75,
          0.9,
          0.75
        ]
      },
      {
        "id": "coffee_table_1",
        "name": "茶几",
        "label": "coffee_table",
        "position": [
          2.1,
          0.0,
          2.85
        ],
        "size": [
          1.1,
          0.45,
          0.55
        ]
      },
      {
        "id": "rug_1",
        "name": "客厅地毯",
        "label": "rug",
        "position": [
          2.2,
          0.01,
          3.1
        ],
        "size": [
          2.8,
          0.02,
          2.0
        ]
      },
      {
        "id": "tv_stand_1",
        "name": "电视柜",
        "label": "tv_stand",
        "position": [
          2.0,
          0.0,
          0.4
        ],
        "size": [
          1.8,
          0.5,
          0.4
        ]
      },
      {
        "id": "sideboard_1",
        "name": "边柜",
        "label": "cabinet",
        "position": [
          5.15,
          0.0,
          1.6
        ],
        "size": [
          0.45,
          0.85,
          1.4
        ]
      },
      {
        "id": "dining_table_1",
        "name": "餐桌",
        "label": "dining_table",
        "position": [
          4.3,
          0.0,
          2.6
        ],
        "size": [
          1.4,
          0.75,
          0.9
        ]
      },
      {
        "id": "chair_1",
        "name": "餐椅A",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          2.0
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "chair_2",
        "name": "餐椅B",
        "label": "chair",
        "position": [
          4.3,
          0.0,
          3.2
        ],
        "size": [
          0.45,
          0.9,
          0.5
        ]
      },
      {
        "id": "desk_1",
        "name": "书桌",
        "label": "desk",
        "position": [
          0.7,
          0.0,
          2.2
        ],
        "size": [
          1.2,
          0.75,
          0.6
        ]
      },
      {
        "id": "plant_1",
        "name": "绿植",
        "label": "plant",
        "position": [
          0.45,
          0.0,
          4.35
        ],
        "size": [
          0.4,
          1.2,
          0.4
        ]
      },
      {
        "id": "floor_lamp_1",
        "name": "落地灯",
        "label": "floor_lamp",
        "position": [
          3.55,
          0.0,
          4.35
        ],
        "size": [
          0.35,
          1.7,
          0.35
        ]
      }
    ],
    "openings": [
      {
        "id": "door_main",
        "type": "door",
        "name": "入户门",
        "position": [
          0.7,
          1.05,
          0.0
        ],
        "rotation": [
          0.0,
          0.0,
          0.0
        ],
        "size": [
          1.0,
          2.1,
          0.12
        ],
        "clearanceDepth": 1.0
      },
      {
        "id": "door_balcony",
        "type": "door",
        "name": "阳台门",
        "position": [
          5.0,
          1.05,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          0.9,
          2.1,
          0.12
        ],
        "clearanceDepth": 0.9
      },
      {
        "id": "window_living",
        "type": "window",
        "name": "客厅落地窗",
        "position": [
          2.4,
          1.2,
          4.8
        ],
        "rotation": [
          0.0,
          180.0,
          0.0
        ],
        "size": [
          2.4,
          2.0,
          0.12
        ],
        "clearanceDepth": 0.4
      },
      {
        "id": "window_side",
        "type": "window",
        "name": "侧窗",
        "position": [
          5.6,
          1.4,
          3.2
        ],
        "rotation": [
          0.0,
          -90.0,
          0.0
        ],
        "size": [
          1.2,
          1.2,
          0.12
        ],
        "clearanceDepth": 0.35
      }
    ]
  }
}
```

### 输出摘要

- 几何 overallStatus：`fail`
- 布局 summary：空间布局需优化，确保通行无阻且家具间距合理。
- 场景 summary：风水：优化客厅风水布局，提升舒适度和采光。；养宠：优化宠物活动空间，确保安全与舒适。；养老：本场景需优化家具布局，确保老人活动安全与舒适。

### 模块A：家具移动后的位置 `layout.moves`
```json
[
  {
    "objectId": "candidate_wardrobe",
    "name": "衣柜",
    "fromPosition": [
      0.55,
      0.0,
      0.55
    ],
    "toPosition": [
      0.5,
      0.0,
      0.508
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "离开入户门净空区，建议移开约 63 cm",
    "source": "geometry"
  }
]
```

### 模块B：布局优化建议 `layout.advices`（中文）
```json
[
  {
    "id": "layout_001",
    "priority": "高",
    "title": "调整衣柜位置",
    "problem": "衣柜位置影响入户门开启，且活动空间不足。",
    "suggestion": "将衣柜向后移动约35cm，避免与入户门冲突，并确保前方有足够的活动空间。",
    "relatedObjectIds": [
      "candidate_wardrobe"
    ]
  },
  {
    "id": "layout_002",
    "priority": "中",
    "title": "优化沙发布局",
    "problem": "沙发与电视柜之间距离过近，影响视线。",
    "suggestion": "将沙发向前移动约30cm，增加与电视柜之间的距离，改善视线。",
    "relatedObjectIds": [
      "sofa_1",
      "tv_stand_1"
    ]
  },
  {
    "id": "layout_003",
    "priority": "中",
    "title": "调整餐桌位置",
    "problem": "餐桌位置与沙发距离过近，影响客厅活动。",
    "suggestion": "将餐桌向后移动约50cm，增加与沙发的距离，提高客厅活动空间。",
    "relatedObjectIds": [
      "dining_table_1"
    ]
  },
  {
    "id": "layout_004",
    "priority": "低",
    "title": "优化茶几位置",
    "problem": "茶几位置靠近电视柜，可能影响电视柜使用。",
    "suggestion": "将茶几向沙发方向移动约20cm，避免与电视柜过于接近。",
    "relatedObjectIds": [
      "coffee_table_1"
    ]
  },
  {
    "id": "layout_005",
    "priority": "低",
    "title": "调整绿植位置",
    "problem": "绿植位置影响侧窗采光。",
    "suggestion": "将绿植向房间内部移动约30cm，避免遮挡侧窗采光。",
    "relatedObjectIds": [
      "plant_1"
    ]
  }
]
```

### 场景选择后的修改建议
- 已选场景：fengshui, pet, elder

```json
{
  "fengshui": [
    {
      "id": "fengshui_001",
      "scenarioId": "fengshui",
      "priority": "高",
      "title": "调整沙发位置避免门冲",
      "reason": "沙发正对入户门，形成门冲，影响风水。",
      "action": "将沙发向后移动约1米，使其背对入户门。",
      "relatedObjectIds": [
        "sofa_1"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_002",
      "scenarioId": "fengshui",
      "priority": "中",
      "title": "优化餐桌布局",
      "reason": "餐桌正对阳台门，影响用餐氛围。",
      "action": "将餐桌向房间内部移动约1.5米，避免正对阳台门。",
      "relatedObjectIds": [
        "dining_table_1"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_003",
      "scenarioId": "fengshui",
      "priority": "中",
      "title": "调整电视柜位置",
      "reason": "电视柜正对侧窗，影响电视观看体验。",
      "action": "将电视柜向房间内部移动约1米，避免正对侧窗。",
      "relatedObjectIds": [
        "tv_stand_1"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_004",
      "scenarioId": "fengshui",
      "priority": "低",
      "title": "增加绿植数量",
      "reason": "绿植数量较少，不利于风水。",
      "action": "在客厅适当位置增加绿植，如茶几旁、沙发角落等。",
      "relatedObjectIds": [],
      "targetPosition": null
    },
    {
      "id": "fengshui_005",
      "scenarioId": "fengshui",
      "priority": "低",
      "title": "调整落地灯位置",
      "reason": "落地灯位置影响采光。",
      "action": "将落地灯向房间内部移动约0.5米，避免遮挡窗户。",
      "relatedObjectIds": [
        "floor_lamp_1"
      ],
      "targetPosition": null
    }
  ],
  "pet": [
    {
      "id": "pet_001",
      "scenarioId": "pet",
      "priority": "高",
      "title": "设置宠物通道",
      "reason": "现有家具布局可能阻挡宠物通行。",
      "action": "在沙发与电视柜之间留出至少50cm的通道，确保宠物可以自由通行。",
      "relatedObjectIds": [
        "sofa_1",
        "tv_stand_1"
      ],
      "targetPosition": null
    },
    {
      "id": "pet_002",
      "scenarioId": "pet",
      "priority": "中",
      "title": "优化窗边活动区",
      "reason": "窗边区域可能存在安全隐患。",
      "action": "在窗边设置宠物专用的活动区域，避免宠物靠近窗户。",
      "relatedObjectIds": [
        "window_living"
      ],
      "targetPosition": null
    },
    {
      "id": "pet_003",
      "scenarioId": "pet",
      "priority": "中",
      "title": "设置进食/休息角落",
      "reason": "宠物需要一个安静舒适的进食和休息角落。",
      "action": "在房间的一角放置宠物床和食水碗，为宠物提供一个专属的休息和进食区域。",
      "relatedObjectIds": [],
      "targetPosition": null
    },
    {
      "id": "pet_004",
      "scenarioId": "pet",
      "priority": "低",
      "title": "避免门摆阻挡",
      "reason": "门摆可能会绊倒宠物。",
      "action": "在门附近设置明显的警示标志，提醒宠物注意门摆。",
      "relatedObjectIds": [
        "door_main",
        "door_balcony"
      ],
      "targetPosition": null
    },
    {
      "id": "pet_005",
      "scenarioId": "pet",
      "priority": "低",
      "title": "减少绊倒风险",
      "reason": "地毯可能存在绊倒风险。",
      "action": "选择防滑地毯，或在地毯上铺设防滑垫，减少宠物绊倒的风险。",
      "relatedObjectIds": [
        "rug_1"
      ],
      "targetPosition": null
    }
  ],
  "elder": [
    {
      "id": "elder_001",
      "scenarioId": "elder",
      "priority": "高",
      "title": "调整沙发位置",
      "reason": "沙发位置影响老人起身时的净空空间。",
      "action": "将沙发向后移动约50cm，确保老人起身时有足够的空间。",
      "relatedObjectIds": [
        "sofa_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_002",
      "scenarioId": "elder",
      "priority": "中",
      "title": "优化餐桌布局",
      "reason": "餐桌位置与沙发距离过近，影响老人行走。",
      "action": "将餐桌向后移动约60cm，增加与沙发的距离。",
      "relatedObjectIds": [
        "dining_table_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_003",
      "scenarioId": "elder",
      "priority": "中",
      "title": "调整单人椅位置",
      "reason": "单人椅位置影响老人行走动线。",
      "action": "将单人椅向前移动约30cm，靠近通道，方便老人行走。",
      "relatedObjectIds": [
        "armchair_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_004",
      "scenarioId": "elder",
      "priority": "低",
      "title": "优化茶几位置",
      "reason": "茶几位置可能影响老人行走。",
      "action": "将茶几向沙发方向移动约20cm，避免与通道过于接近。",
      "relatedObjectIds": [
        "coffee_table_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_005",
      "scenarioId": "elder",
      "priority": "低",
      "title": "调整绿植位置",
      "reason": "绿植位置可能影响老人行走。",
      "action": "将绿植向房间内部移动约30cm，避免遮挡通道。",
      "relatedObjectIds": [
        "plant_1"
      ],
      "targetPosition": null
    }
  ]
}
```

---

## 案例（全屋模式）：rich_family_living_dining

### 耗时

- Phase1 room-layout：**0.031s**
- Phase2 scenario-advice：**0.0s**
- 合计：**0.031s**

### 输入（`POST /api/room/room-layout`）

```json
{
  "enableAgents": true,
  "scene": {
    "sceneId": "rich_family_living_dining",
    "room": {
      "width": 5.6,
      "depth": 4.8,
      "height": 2.8
    },
    "objectCount": 12,
    "openingCount": 4
  }
}
```

### 输出摘要

- mode：`room`
- overallStatus：`fail`
- feedback：全屋检测发现 7 件家具存在硬冲突（碰撞/堵门/越界等），建议优先调整。
- layout.summary：全屋发现 7 处建议移动，并已给出布局优化建议。
- objectChecks：10 件
- moves：7

### objectChecks（有问题的家具）

```json
[
  {
    "objectId": "sofa_1",
    "name": "三人沙发",
    "overallStatus": "fail",
    "issues": [
      {
        "ruleId": "accessibility",
        "status": "fail",
        "message": "遮挡客厅落地窗"
      },
      {
        "ruleId": "clearance",
        "status": "warn",
        "message": "前方活动空间不足（30 cm，需 ≥ 60 cm）"
      }
    ]
  },
  {
    "objectId": "armchair_1",
    "name": "单人椅",
    "overallStatus": "fail",
    "issues": [
      {
        "ruleId": "collision",
        "status": "fail",
        "message": "与餐椅B发生重叠"
      }
    ]
  },
  {
    "objectId": "tv_stand_1",
    "name": "电视柜",
    "overallStatus": "fail",
    "issues": [
      {
        "ruleId": "accessibility",
        "status": "fail",
        "message": "进入入户门开启区域"
      }
    ]
  },
  {
    "objectId": "sideboard_1",
    "name": "边柜",
    "overallStatus": "fail",
    "issues": [
      {
        "ruleId": "collision",
        "status": "fail",
        "message": "与餐桌发生重叠"
      }
    ]
  },
  {
    "objectId": "dining_table_1",
    "name": "餐桌",
    "overallStatus": "fail",
    "issues": [
      {
        "ruleId": "collision",
        "status": "fail",
        "message": "与边柜、餐椅A、餐椅B发生重叠"
      },
      {
        "ruleId": "clearance",
        "status": "warn",
        "message": "前方活动空间不足（0 cm，需 ≥ 75 cm）；后方活动空间不足（0 cm，需 ≥ 75 cm）；右侧活动空间不足（0 cm，需 ≥ 75 cm）"
      }
    ]
  },
  {
    "objectId": "chair_1",
    "name": "餐椅A",
    "overallStatus": "fail",
    "issues": [
      {
        "ruleId": "collision",
        "status": "fail",
        "message": "与餐桌发生重叠"
      }
    ]
  },
  {
    "objectId": "chair_2",
    "name": "餐椅B",
    "overallStatus": "fail",
    "issues": [
      {
        "ruleId": "collision",
        "status": "fail",
        "message": "与单人椅、餐桌发生重叠"
      }
    ]
  }
]
```

### layout.moves

```json
[
  {
    "objectId": "sofa_1",
    "name": "三人沙发",
    "fromPosition": [
      2.0,
      0.0,
      3.9
    ],
    "toPosition": [
      1.784,
      0.0,
      3.061
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "离开客厅落地窗净空区，建议移开约 87 cm",
    "source": "geometry"
  },
  {
    "objectId": "armchair_1",
    "name": "单人椅",
    "fromPosition": [
      3.7,
      0.0,
      3.5
    ],
    "toPosition": [
      3.655,
      0.0,
      3.522
    ],
    "fromRotation": [
      0.0,
      0.0,
      45.0
    ],
    "toRotation": [
      0.0,
      0.0,
      45.0
    ],
    "reason": "与餐椅B重叠，建议分离约 5 cm",
    "source": "geometry"
  },
  {
    "objectId": "tv_stand_1",
    "name": "电视柜",
    "fromPosition": [
      2.0,
      0.0,
      0.4
    ],
    "toPosition": [
      2.179,
      0.0,
      0.378
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "离开入户门净空区，建议移开约 18 cm",
    "source": "geometry"
  },
  {
    "objectId": "sideboard_1",
    "name": "边柜",
    "fromPosition": [
      5.15,
      0.0,
      1.6
    ],
    "toPosition": [
      5.231,
      0.0,
      1.505
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "与餐桌重叠，建议分离约 12 cm",
    "source": "geometry"
  },
  {
    "objectId": "dining_table_1",
    "name": "餐桌",
    "fromPosition": [
      4.3,
      0.0,
      2.6
    ],
    "toPosition": [
      4.3,
      0.0,
      2.75
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "与边柜、餐椅A、餐椅B重叠，建议分离约 15 cm",
    "source": "geometry"
  },
  {
    "objectId": "chair_1",
    "name": "餐椅A",
    "fromPosition": [
      4.3,
      0.0,
      2.0
    ],
    "toPosition": [
      4.3,
      0.0,
      1.85
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "与餐桌重叠，建议分离约 15 cm",
    "source": "geometry"
  },
  {
    "objectId": "chair_2",
    "name": "餐椅B",
    "fromPosition": [
      4.3,
      0.0,
      3.2
    ],
    "toPosition": [
      4.3,
      0.0,
      3.35
    ],
    "fromRotation": [
      0.0,
      0.0,
      0.0
    ],
    "toRotation": [
      0.0,
      0.0,
      0.0
    ],
    "reason": "与单人椅、餐桌重叠，建议分离约 15 cm",
    "source": "geometry"
  }
]
```

### layout.advices

```json
[
  {
    "id": "room_001",
    "priority": "高",
    "title": "优化三人沙发的摆放",
    "problem": "遮挡客厅落地窗",
    "suggestion": "该位置会遮挡窗户，建议挪开以保留采光与开启空间。",
    "relatedObjectIds": [
      "sofa_1"
    ]
  },
  {
    "id": "room_002",
    "priority": "高",
    "title": "优化单人椅的摆放",
    "problem": "与餐椅B发生重叠",
    "suggestion": "该家具与餐椅B发生重叠，请调整摆放位置（建议移开约 5 cm）。",
    "relatedObjectIds": [
      "armchair_1"
    ]
  },
  {
    "id": "room_003",
    "priority": "高",
    "title": "优化电视柜的摆放",
    "problem": "进入入户门开启区域",
    "suggestion": "该位置会影响房门正常开启，建议远离门口区域。",
    "relatedObjectIds": [
      "tv_stand_1"
    ]
  },
  {
    "id": "room_004",
    "priority": "高",
    "title": "优化边柜的摆放",
    "problem": "与餐桌发生重叠",
    "suggestion": "该家具与餐桌发生重叠，请调整摆放位置（建议移开约 8 cm）。",
    "relatedObjectIds": [
      "sideboard_1"
    ]
  },
  {
    "id": "room_005",
    "priority": "高",
    "title": "优化餐桌的摆放",
    "problem": "与边柜、餐椅A、餐椅B发生重叠",
    "suggestion": "该家具与边柜、餐椅A、餐椅B发生重叠，请调整摆放位置（建议移开约 10 cm）。",
    "relatedObjectIds": [
      "dining_table_1"
    ]
  },
  {
    "id": "room_006",
    "priority": "高",
    "title": "优化餐椅A的摆放",
    "problem": "与餐桌发生重叠",
    "suggestion": "该家具与餐桌发生重叠，请调整摆放位置（建议移开约 10 cm）。",
    "relatedObjectIds": [
      "chair_1"
    ]
  }
]
```

### 场景建议（mode=room, elder+fengshui）

- summary：养老：围绕养老场景给出可执行调整建议。；风水：围绕风水场景给出可执行调整建议。

```json
{
  "elder": [
    {
      "id": "elder_000",
      "scenarioId": "elder",
      "priority": "高",
      "title": "先落实几何安全移动",
      "reason": "场景优化前应先消除碰撞/堵门等硬冲突。",
      "action": "请先将三人沙发从 [2.0, 0.0, 3.9] 调整到 [1.784, 0.0, 3.061]：离开客厅落地窗净空区，建议移开约 87 cm",
      "relatedObjectIds": [
        "sofa_1"
      ],
      "targetPosition": [
        1.784,
        0.0,
        3.061
      ]
    },
    {
      "id": "elder_001",
      "scenarioId": "elder",
      "priority": "高",
      "title": "保证座位前方起身净空",
      "reason": "老人起身与转身需要更充足的前方空间，降低跌倒风险。",
      "action": "若主要家具靠近座位区，请至少留出 0.6 米前方净空，并避开门口堆物。",
      "relatedObjectIds": [
        "sofa_1",
        "armchair_1",
        "coffee_table_1",
        "rug_1"
      ],
      "targetPosition": null
    },
    {
      "id": "elder_002",
      "scenarioId": "elder",
      "priority": "高",
      "title": "保持主要通行路径连续",
      "reason": "适老化布局需要沙发、门与主要座位之间连续可达。",
      "action": "保留一条不少于 0.9 米宽的连续通道，避免家具边角侵入动线。",
      "relatedObjectIds": [
        "door_main",
        "door_balcony"
      ],
      "targetPosition": null
    }
  ],
  "fengshui": [
    {
      "id": "fengshui_001",
      "scenarioId": "fengshui",
      "priority": "中",
      "title": "保持入户视线通透",
      "reason": "入口正对高大遮挡会带来压迫感，影响空间气场与第一观感。",
      "action": "避免在入户门正前方摆放高于 1.5 米的柜体；可侧移形成斜向缓冲。",
      "relatedObjectIds": [
        "door_main",
        "door_balcony"
      ],
      "targetPosition": null
    },
    {
      "id": "fengshui_002",
      "scenarioId": "fengshui",
      "priority": "中",
      "title": "主座尽量背靠实墙",
      "reason": "沙发或主座背后有实墙更稳定，减少背后开门窗的不安感。",
      "action": "优先让主要座位靠实墙；若背后是门窗，建议旋转朝向或后移靠墙。",
      "relatedObjectIds": [
        "sofa_1",
        "armchair_1",
        "coffee_table_1",
        "rug_1"
      ],
      "targetPosition": null
    }
  ]
}
```

