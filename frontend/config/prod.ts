import type { UserConfigExport } from '@tarojs/cli'

// 生产环境配置
export default {
  mini: {},
  h5: {
    // 构建产物拆包，利于首屏 < 3s 的性能底线
    webpackChain(chain) {
      chain.optimization.splitChunks({
        chunks: 'all',
        cacheGroups: {
          vendors: {
            name: 'vendors',
            test: /[\\/]node_modules[\\/]/,
            priority: 10,
          },
        },
      })
    },
  },
} satisfies UserConfigExport<'webpack5'>
