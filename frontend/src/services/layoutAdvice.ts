import type { RoomLayoutAdvice, SceneSnapshot, Vector3 } from '@/types/scene'
export function buildMockLayoutAdvice(snapshot: SceneSnapshot, selectedId?: string): RoomLayoutAdvice {
  const target = snapshot.objects.find((item) => item.instanceId === selectedId) ?? [...snapshot.objects].reverse().find((item) => !item.placement.isExisting) ?? snapshot.objects[0]
  const from = (target?.transform.position ?? [3, .4, 2.1]) as Vector3
  const to: Vector3 = [from[0] > 3 ? Math.max(.4, from[0] - .24) : Math.min(5.6, from[0] + .24), from[1], from[2]]
  return { mode: 'room', overallStatus: 'warn', objectChecks: [], feedback: '空间接口不可用，当前显示确定性 Mock 建议。', layout: { moves: target ? [{ objectId: target.instanceId, name: target.semantic.name, fromPosition: from, toPosition: to, fromRotation: target.transform.rotation, toRotation: target.transform.rotation, reason: '横向移动 24cm，为 room6 主通道留出连续空间。', source: 'mock' }] : [], advices: [
    { id: 'clearance', priority: '高', title: '放宽主通道', problem: '新增家具靠近核心活动区。', suggestion: '移动选中家具，保持主要行走路径连续。', relatedObjectIds: target ? [target.instanceId] : [] },
    { id: 'fit', priority: '中', title: '尺寸适配正常', problem: '模型尺寸已写入快照。', suggestion: '保持真实尺寸比例，避免场景失真。', relatedObjectIds: target ? [target.instanceId] : [] },
    { id: 'style', priority: '低', title: '补充材质层次', problem: '当前大件以中性色和木质为主。', suggestion: '增加低饱和软装作为视觉焦点。', relatedObjectIds: target ? [target.instanceId] : [] },
  ], summary: '优先处理动线，再保持真实尺寸，最后补充色彩和材质层次。' }, scenarioOptions: [] }
}
