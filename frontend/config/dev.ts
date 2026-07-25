import type { UserConfigExport } from '@tarojs/cli'

// 开发环境配置
export default {
  logger: {
    quiet: false,
    stats: true,
  },
  mini: {},
  h5: {
    // —— 修复白屏根因 ——
    // 现象：访问 / 返回的是 serve-index 的“listing directory /”目录列表页，
    //      而不是 Taro 编译出的 index.html（它在 devMiddleware 内存里）。
    // 原因：dev-server 的 static 静态目录服务对空的 dist/ 目录启用了目录列表，
    //      抢在 devMiddleware 之前把 / 的请求截胡了。
    // 解法：关闭 static 目录服务与目录列表，让 devMiddleware 的 index.html 正常兜底。
    devServer: {
      // 关闭对 dist / .taro remote 目录的静态服务（避免 serve-index 截胡根路径）
      static: false,
      // 明确 SPA 兜底：所有未命中的路由回退到 devMiddleware 内存里的 index.html
      historyApiFallback: {
        index: '/index.html',
        disableDotRule: true,
      },
      devMiddleware: {
        // 明确入口文件名，确保 / 命中内存中的 index.html
        index: 'index.html',
        // 关闭目录列表，杜绝 serve-index 行为
        serverSideRender: false,
      },
      // 允许被内置预览面板 / 局域网访问
      allowedHosts: 'all',
      host: '0.0.0.0',
      proxy: [
        {
          context: ['/api', '/sample_data', '/outputs'],
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      ],
    },
  },
} satisfies UserConfigExport<'webpack5'>
