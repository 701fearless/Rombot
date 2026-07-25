// ID 生成：前缀 + 时间戳(base36) + 随机串，前端本地唯一即可（真实后端接管后由服务端发号）
export function genId(prefix: string): string {
  const ts = Date.now().toString(36)
  const rand = Math.random().toString(36).slice(2, 8)
  return `${prefix}_${ts}_${rand}`
}
