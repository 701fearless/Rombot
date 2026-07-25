import path from 'path'
import { defineConfig, type UserConfigExport } from '@tarojs/cli'
import devConfig from './dev'
import prodConfig from './prod'

// Taro 4 项目主配置
export default defineConfig<'webpack5'>(async (merge, { command: _command, mode: _mode }) => {
  const baseConfig: UserConfigExport<'webpack5'> = {
    projectName: 'home-ai-miniapp',
    date: '2026-07-22',
    // 组件样式按真实移动端逻辑像素书写（48px 触控区、16px 页面边距）。
    // 使用 375 基准，避免 750 设计稿模式把所有尺寸在 H5/小程序中缩小一半。
    designWidth: 375,
    deviceRatio: {
      640: 2.34 / 2,
      750: 1,
      375: 2,
      828: 1.81 / 2,
    },
    sourceRoot: 'src',
    outputRoot: 'dist',
    plugins: ['@tarojs/plugin-framework-react'],
    defineConstants: {},
    copy: {
      patterns: [
        // hero 视频：webpack 默认不处理 mp4，原样拷贝后按运行路径引用
        // 注意：copy.to 相对项目根（非 outputRoot），需显式带 dist 前缀
        // tabBar 图标无需拷贝：Taro 会把 iconPath 自动打包进 static/images/assets/
        { from: 'src/assets/video', to: 'dist/assets/video' },
      ],
      options: {},
    },
    framework: 'react',
    compiler: 'webpack5',
    cache: {
      enable: false,
    },
    // 路径别名：@ → src（与 tsconfig.json paths 保持一致）
    alias: {
      '@': path.resolve(__dirname, '..', 'src'),
    },
    // sass：Taro 4 内建 dart-sass 支持（依赖根目录 sass 包）
    sass: {
      data: '',
    },
    mini: {
      postcss: {
        pxtransform: {
          enable: true,
          config: {},
        },
        cssModules: {
          enable: false,
        },
      },
    },
    h5: {
      // 相对路径：生产构建后用任意静态服务器 serve dist 都能正确加载资源，
      // 避免绝对路径 '/' 在子目录部署或某些静态服务器下 404。
      publicPath: './',
      staticDirectory: 'static',
      output: {
        filename: 'js/[name].[hash:8].js',
        chunkFilename: 'js/[name].[chunkhash:8].js',
      },
      postcss: {
        autoprefixer: {
          enable: true,
          config: {},
        },
        cssModules: {
          enable: false,
        },
      },
    },
  }
  if (process.env.NODE_ENV === 'development') {
    // 开发模式合并 dev 配置
    return merge({}, baseConfig, devConfig)
  }
  return merge({}, baseConfig, prodConfig)
})
