import type { RoomLayoutAdvice, SceneSnapshot } from '@/types/scene'

export function buildMockLayoutAdvice(snapshot: SceneSnapshot, selectedId?: string): RoomLayoutAdvice {
  const target = snapshot.objects.find((item) => item.instanceId === selectedId)
    ?? [...snapshot.objects].reverse().find((item) => !item.placement.isExisting)
    ?? snapshot.objects[0]
  const position = target?.transform.position ?? [3, 0.4, 2.1]
  const moveX = position[0] > 3 ? Math.max(0.4, position[0] - 0.24) : Math.min(5.6, position[0] + 0.24)
  const moves = target ? [{
    objectId: target.instanceId,
    name: target.semantic.name,
    fromPosition: [...position] as [number, number, number],
    toPosition: [moveX, position[1], position[2]] as [number, number, number],
    fromRotation: [...target.transform.rotation] as [number, number, number],
    toRotation: [...target.transform.rotation] as [number, number, number],
    reason: '向侧面移动 24cm，为 room6 的主通道留出更完整的连续空间。',
    source: 'mock' as const,
  }] : []

  return {
    mode: 'room', overallStatus: 'warn', objectChecks: [],
    feedback: '方案已保存。当前为结构化 Mock 建议，后续可直接替换为真实布局推理。',
    layout: {
      moves,
      advices: [
        { id: 'mock_clearance', priority: '高', title: '放宽主通道', problem: '新增家具与客厅核心活动区距离偏近。', suggestion: '将选中家具横向移动 24cm，保持主要行走路径连续。', relatedObjectIds: target ? [target.instanceId] : [] },
        { id: 'mock_fit', priority: '中', title: '尺寸适配正常', problem: '家具尺寸已按识别结果写入快照。', suggestion: '保持当前缩放，避免演示模型与实际尺寸失真。', relatedObjectIds: target ? [target.instanceId] : [] },
        { id: 'mock_style', priority: '低', title: '补充材质层次', problem: '当前大件以中性色和木质为主。', suggestion: '可增加一件低饱和软装作为视觉焦点。', relatedObjectIds: target ? [target.instanceId] : [] },
      ],
      summary: '优先处理动线，再保持真实尺寸，最后补充色彩与材质层次。',
    },
    scenarioOptions: [],
  }
}
