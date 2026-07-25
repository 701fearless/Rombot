export function differenceHashFromRgba(rgba: Uint8ClampedArray, width = 9, height = 8): string {
  if (width !== 9 || height !== 8 || rgba.length !== width * height * 4) throw new Error('dHash expects a 9x8 RGBA frame')
  const grayscale: number[] = []
  for (let i = 0; i < rgba.length; i += 4) grayscale.push(Math.round(.299 * rgba[i] + .587 * rgba[i + 1] + .114 * rgba[i + 2]))
  let value = 0n
  for (let row = 0; row < 8; row += 1) for (let column = 0; column < 8; column += 1) { const offset = row * 9 + column; value = (value << 1n) | BigInt(grayscale[offset] > grayscale[offset + 1]) }
  return value.toString(16).padStart(16, '0')
}
export function computeVideoDHash(video: HTMLVideoElement): string {
  if (!video.videoWidth || !video.videoHeight || video.readyState < 2) throw new Error('视频画面尚未准备好')
  const canvas = document.createElement('canvas'); canvas.width = 9; canvas.height = 8
  const context = canvas.getContext('2d', { willReadFrequently: true }); if (!context) throw new Error('浏览器无法读取视频画面')
  context.drawImage(video, 0, 0, 9, 8); return differenceHashFromRgba(context.getImageData(0, 0, 9, 8).data)
}
