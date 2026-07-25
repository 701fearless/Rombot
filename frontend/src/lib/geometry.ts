export interface Point {
  x: number
  y: number
}

export function coverTagPosition(
  normalizedPosition: [number, number],
  sourceSize: { width: number; height: number },
  containerSize: { width: number; height: number },
): Point {
  if (
    sourceSize.width <= 0 ||
    sourceSize.height <= 0 ||
    containerSize.width <= 0 ||
    containerSize.height <= 0
  ) {
    return { x: containerSize.width / 2, y: containerSize.height / 2 }
  }

  const scale = Math.max(
    containerSize.width / sourceSize.width,
    containerSize.height / sourceSize.height,
  )
  const renderedWidth = sourceSize.width * scale
  const renderedHeight = sourceSize.height * scale
  const offsetX = (containerSize.width - renderedWidth) / 2
  const offsetY = (containerSize.height - renderedHeight) / 2

  return {
    x: offsetX + normalizedPosition[0] * renderedWidth,
    y: offsetY + normalizedPosition[1] * renderedHeight,
  }
}

export function containTagPosition(
  normalizedPosition: [number, number],
  sourceSize: { width: number; height: number },
  containerSize: { width: number; height: number },
): Point {
  if (
    sourceSize.width <= 0 ||
    sourceSize.height <= 0 ||
    containerSize.width <= 0 ||
    containerSize.height <= 0
  ) {
    return { x: containerSize.width / 2, y: containerSize.height / 2 }
  }

  const scale = Math.min(
    containerSize.width / sourceSize.width,
    containerSize.height / sourceSize.height,
  )
  const renderedWidth = sourceSize.width * scale
  const renderedHeight = sourceSize.height * scale

  return {
    x: (containerSize.width - renderedWidth) / 2 + normalizedPosition[0] * renderedWidth,
    y: (containerSize.height - renderedHeight) / 2 + normalizedPosition[1] * renderedHeight,
  }
}
