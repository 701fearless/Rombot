// 全局应用配置（信息架构 2026-07-25 修订版）
// Tab 结构：灵感（房屋记忆 + Feed）→ 我的家（资产池）→ 发现（场景改造）→ 资产（个人建模入口）
// 「我的」/比价/下单已整线删除，推荐单品唯一出口 = 直达抖音商城外跳
// tabBar 配色与 tokens.scss 三色系统保持一致（原生配置只能写色值）
export default defineAppConfig({
  pages: [
    // —— 4 个 Tab ——
    'pages/discover/index', // Tab1 灵感（房屋记忆 + 家居类型筛选 Feed）
    'pages/myhome/index', //   Tab2 我的家（常驻资产池：方形 3D 空间 + 平铺家具库）
    'pages/direction/index', // Tab3 发现（细分客群方向：养宠/养娃/动线/风水/配色 → 三动作）
    'pages/remodel/index', //  Tab4 我的（个人信息 + 四个建模入口）
    // —— 全屏动作流页 / 独立功能页（不进 tabBar）——
    'pages/discover/detail/index', // 单品详情页（灵感 Feed 点击进入）
    'pages/discover/scene/index', // 场景详情页（视频复现：场景下挂家具元素）
    'pages/flow/recognize/index', // 识别流
    'pages/flow/place/index', //     摆放/替换流
    'pages/flow/suggest/index', //   AI 建议流
    'pages/flow/recommend/index', // 荐单品流（直达抖音，取代 order）
    'pages/flow/complete/index', //  整屋补全流
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#F7F4EF',
    navigationBarTitleText: '即刻试摆',
    navigationBarTextStyle: 'black',
    backgroundColor: '#F7F4EF',
  },
  tabBar: {
    color: '#7B817A',
    selectedColor: '#344238',
    backgroundColor: '#FFFDF9',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/discover/index',
        text: '灵感',
        iconPath: 'assets/tabbar/discover.png',
        selectedIconPath: 'assets/tabbar/discover-active.png',
      },
      {
        pagePath: 'pages/myhome/index',
        text: '我的家',
        iconPath: 'assets/tabbar/myhome.png',
        selectedIconPath: 'assets/tabbar/myhome-active.png',
      },
      {
        pagePath: 'pages/direction/index',
        text: '发现',
        iconPath: 'assets/tabbar/wand.png',
        selectedIconPath: 'assets/tabbar/wand-active.png',
      },
      {
        pagePath: 'pages/remodel/index',
        text: '我的',
        iconPath: 'assets/tabbar/remodel.png',
        selectedIconPath: 'assets/tabbar/remodel-active.png',
      },
    ],
  },
})
