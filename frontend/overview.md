# 移动端 UI 效果适配（P0 + P1）实施总览

**预览**:http://localhost:10086/(dist 已是最新构建 app.6727a8f2；建议 Chrome DevTools 切手机模式或直接手机访问局域网 IP)

## 完成内容

| 项 | 实现 | 涉及文件 |
|---|---|---|
| P0-1 全局按压反馈 | 所有可点卡片/按钮/pill 加 `:active` 凹陷(scale + 浮雕 inset);app.tsx 注册 body touchstart 使 iOS 生效 | 12 个 scss + app.tsx |
| P0-2 Hero 视频移动化 | 触摸端 autoplay+loop+muted；大卡横向触摸接管 scrub(12px 阈值），松手 2s 恢复；`touch-action: pan-y` 竖滚零干扰；PC mousemove 不变 | EntryHero tsx/scss |
| P0-3 书架滚动抽书 | 滚动居中自动抽出(rect 实测 + 14px 滞回）；首卡脉冲演示（避开开屏 3.8s)；小屏封面锁 148PX 保证可滚动 | CoverShelf tsx/scss、discover |
| P1-1 震动反馈 | 吸附跳变轻震、落位中震、抽书轻震；H5 navigator.vibrate / 小程序 vibrateShort | utils/haptics.ts（新）、place、CoverShelf |
| P1-2 检测框自动演示 | 触摸端入场后自动展开第一框 1.6s（用户已交互则跳过） | HeroScan |
| P1-3 Feed 滚动入场 | Reveal 组件（H5 IntersectionObserver，小程序降级直出）,stagger 70ms | components/Reveal（新）、discover |

## 关键决策

- **Taro px→rem 缩放大坑**:390px 屏上 px 被压到 ≈0.4 倍，书架不溢出不可滚。解法：媒体查询内用大写 `PX` 锁真实像素；H5 布局计算一律 getBoundingClientRect 实测。
- **手机端视频走 autoplay 而非 seek**(6MB mp4 手机端 seek 解码卡）；React muted prop 不可靠，手动设 `v.muted`。
- 触摸 scrub 监听挂卡片而非 window + `touch-action: pan-y`，免 preventDefault 与滚动冲突。

## 验证（Playwright 触摸仿真，全部通过）

- 视频自动播放（currentTime 递增）、书架可滚（684>377)、滚动抽出"新中式书房"、脉冲"法式客厅"、:active 规则在产物 CSS、零 JS 报错
- PC 回归：不 autoplay、mouse scrub 正常（t=0.56)、书架无自动抽出

## 待办（P2，未做）

- 详情页轮播换 Taro Swiper（手势滑动）
- 陀螺仪视差（需权限弹窗，谨慎）

## 备注

- 期间发现 EmbossCard/index.scss 被外部还原过一次，已补回并 grep 复核全部 12 个 scss 标记在位。
