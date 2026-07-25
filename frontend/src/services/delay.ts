// 服务层内部工具：模拟网络延迟（300~600ms），接真实后端后删除
export function mockDelay<T>(data: T): Promise<T> {
  const ms = 300 + Math.random() * 300
  return new Promise((resolve) => setTimeout(() => resolve(data), ms))
}
