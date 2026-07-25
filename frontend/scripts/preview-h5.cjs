#!/usr/bin/env node
/**
 * 零依赖 H5 静态预览服务器
 * ------------------------------------------------------------
 * 为什么需要它：
 *   Taro 4.2.1 的 webpack-dev-server 在本项目（含中文路径）下，
 *   会被 serve-index 中间件对空 dist 目录做“目录列表”，抢占根路径 /，
 *   导致浏览器打开只看到一片空白（listing directory /）。
 *   本脚本用生产构建产物 dist/ 直接 serve，行为可控：
 *     - 只 serve 文件，绝不做目录列表
 *     - 命中目录时返回其下的 index.html
 *     - 未命中的路由一律 fallback 到根 index.html（SPA 路由）
 *     - 正确的 Content-Type，避免 JS 被当成 text/plain 不执行
 *
 * 用法：
 *   node scripts/preview-h5.cjs [port] [rootDir]
 *   默认 port=4400, rootDir=dist
 */
const http = require('http')
const fs = require('fs')
const path = require('path')

const PORT = Number(process.argv[2]) || 4400
const ROOT = path.resolve(process.cwd(), process.argv[3] || 'dist')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject',
  '.map': 'application/json; charset=utf-8',
}

const INDEX = path.join(ROOT, 'index.html')

function send(res, status, body, headers = {}) {
  res.writeHead(status, headers)
  res.end(body)
}

function serveFile(res, filePath, req) {
  const ext = path.extname(filePath).toLowerCase()
  const type = MIME[ext] || 'application/octet-stream'
  const size = fs.statSync(filePath).size

  // Range 支持（视频/音频 seek 必需：Chrome 无 Accept-Ranges 会把 seekable 标成 [0,0]）
  const range = req && req.headers.range
  if (range) {
    const m = /bytes=(\d*)-(\d*)/.exec(range)
    if (m) {
      let start = m[1] ? parseInt(m[1], 10) : 0
      let end = m[2] ? parseInt(m[2], 10) : size - 1
      if (m[1] === '' && m[2] !== '') {
        // 后缀形式 bytes=-N：最后 N 字节
        start = Math.max(0, size - parseInt(m[2], 10))
        end = size - 1
      }
      if (start >= size || end >= size || start > end) {
        res.writeHead(416, { 'Content-Range': `bytes */${size}` })
        res.end()
        return
      }
      res.writeHead(206, {
        'Content-Type': type,
        'Cache-Control': 'no-cache',
        'Accept-Ranges': 'bytes',
        'Content-Range': `bytes ${start}-${end}/${size}`,
        'Content-Length': end - start + 1,
      })
      fs.createReadStream(filePath, { start, end }).pipe(res)
      return
    }
  }

  res.writeHead(200, {
    'Content-Type': type,
    'Cache-Control': 'no-cache',
    'Accept-Ranges': 'bytes',
    'Content-Length': size,
  })
  fs.createReadStream(filePath).pipe(res)
}

function serveIndexFallback(res) {
  fs.readFile(INDEX, (err, data) => {
    if (err) {
      send(res, 500, 'index.html not found in dist. 请先运行: npx taro build --type h5')
      return
    }
    send(res, 200, data, { 'Content-Type': MIME['.html'], 'Cache-Control': 'no-cache' })
  })
}

const server = http.createServer((req, res) => {
  // 去掉 query / hash，解码中文/空格
  let urlPath = decodeURIComponent((req.url || '/').split('?')[0].split('#')[0])
  if (urlPath === '/') {
    serveIndexFallback(res)
    return
  }

  // 防目录穿越
  const safePath = path.normalize(urlPath).replace(/^(\.\.[\/\\])+/, '')
  let filePath = path.join(ROOT, safePath)

  fs.stat(filePath, (err, stat) => {
    if (!err && stat.isFile()) {
      serveFile(res, filePath, req)
      return
    }
    if (!err && stat.isDirectory()) {
      // 目录 → 返回该目录的 index.html（绝不列目录）
      const dirIndex = path.join(filePath, 'index.html')
      if (fs.existsSync(dirIndex)) {
        serveFile(res, dirIndex, req)
        return
      }
    }
    // 静态资源（有后缀）没找到 → 真 404
    if (path.extname(safePath)) {
      send(res, 404, 'Not Found: ' + safePath)
      return
    }
    // 无后缀的路由 → SPA fallback 到根 index.html
    serveIndexFallback(res)
  })
})

server.listen(PORT, '0.0.0.0', () => {
  console.log('==================================================')
  console.log('  H5 预览服务器已启动 (零依赖静态服务)')
  console.log('  本地访问:  http://localhost:' + PORT + '/')
  console.log('  serve 目录: ' + ROOT)
  console.log('==================================================')
})
