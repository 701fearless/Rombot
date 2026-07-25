import { PropsWithChildren, useEffect } from 'react'
import { useLaunch } from '@tarojs/taro'
import '@nutui/nutui-react-taro/dist/style.css'
import './app.scss'

function App({ children }: PropsWithChildren) {
  useLaunch(() => {})

  useEffect(() => {
    if (process.env.TARO_ENV === 'h5') {
      const noop = () => {}
      document.body.addEventListener('touchstart', noop, { passive: true })
      return () => document.body.removeEventListener('touchstart', noop)
    }
    return undefined
  }, [])

  return children
}

export default App
