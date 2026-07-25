import { Image, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useEffect, useState } from 'react'
import discoverIcon from '@/assets/tabbar/discover.png'
import discoverActiveIcon from '@/assets/tabbar/discover-active.png'
import myhomeIcon from '@/assets/tabbar/myhome.png'
import myhomeActiveIcon from '@/assets/tabbar/myhome-active.png'
import wandIcon from '@/assets/tabbar/wand.png'
import wandActiveIcon from '@/assets/tabbar/wand-active.png'
import remodelIcon from '@/assets/tabbar/remodel.png'
import remodelActiveIcon from '@/assets/tabbar/remodel-active.png'
import './index.scss'

type TabKey = 'discover' | 'myhome' | 'direction' | 'remodel'

const TABS: Array<{
  key: TabKey
  label: string
  url: string
  icon: string
  activeIcon: string
}> = [
  {
    key: 'discover',
    label: '灵感',
    url: '/pages/discover/index',
    icon: discoverIcon,
    activeIcon: discoverActiveIcon,
  },
  {
    key: 'myhome',
    label: '我的家',
    url: '/pages/myhome/index',
    icon: myhomeIcon,
    activeIcon: myhomeActiveIcon,
  },
  {
    key: 'direction',
    label: '发现',
    url: '/pages/direction/index',
    icon: wandIcon,
    activeIcon: wandActiveIcon,
  },
  {
    key: 'remodel',
    label: '我的',
    url: '/pages/remodel/index',
    icon: remodelIcon,
    activeIcon: remodelActiveIcon,
  },
]

function readPath() {
  if (process.env.TARO_ENV === 'h5' && typeof window !== 'undefined') {
    const hash = window.location.hash.replace(/^#/, '')
    return hash.split('?')[0] || '/pages/discover/index'
  }

  const pages = Taro.getCurrentPages?.()
  const current = pages?.[pages.length - 1]
  return current?.route ? `/${current.route}` : '/pages/discover/index'
}

function resolveActive(path: string): TabKey {
  if (path.startsWith('/pages/myhome') || path.startsWith('/pages/flow/place')) return 'myhome'
  if (
    path.startsWith('/pages/direction') ||
    path.startsWith('/pages/flow/suggest') ||
    path.startsWith('/pages/flow/recommend') ||
    path.startsWith('/pages/flow/complete')
  ) {
    return 'direction'
  }
  if (path.startsWith('/pages/remodel') || path.startsWith('/pages/flow/recognize')) return 'remodel'
  return 'discover'
}

export default function AppTabBar() {
  const [path, setPath] = useState(readPath)
  const active = resolveActive(path)

  useDidShow(() => {
    setPath(readPath())
  })

  useEffect(() => {
    if (process.env.TARO_ENV !== 'h5') return undefined

    const sync = () => setPath(readPath())
    window.addEventListener('hashchange', sync)
    window.addEventListener('popstate', sync)
    sync()

    return () => {
      window.removeEventListener('hashchange', sync)
      window.removeEventListener('popstate', sync)
    }
  }, [])

  const goTab = (url: string) => {
    if (path === url) return
    setPath(url)
    if (process.env.TARO_ENV === 'h5' && typeof window !== 'undefined') {
      window.location.hash = url
      return
    }
    Taro.switchTab({ url })
  }

  return (
    <View className='app-tabbar'>
      {TABS.map((tab) => {
        const isActive = active === tab.key
        return (
          <View
            key={tab.key}
            className={`app-tabbar__item ${isActive ? 'is-active' : ''}`}
            onClick={() => goTab(tab.url)}
          >
            <View className='app-tabbar__icon-shell'>
              <Image
                className='app-tabbar__icon'
                src={isActive ? tab.activeIcon : tab.icon}
                mode='aspectFit'
              />
            </View>
            <Text className={`app-tabbar__label ${isActive ? 'is-active' : ''}`}>
              {tab.label}
            </Text>
          </View>
        )
      })}
    </View>
  )
}
