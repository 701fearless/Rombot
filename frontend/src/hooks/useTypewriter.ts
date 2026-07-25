// 打字机效果 hook：延迟 startDelay 后按 speed 逐字 reveal
// 参考 Mainframe hero：光标在 done 后消失
import { useEffect, useState } from 'react'

export interface TypewriterResult {
  displayed: string
  done: boolean
}

export function useTypewriter(text: string, speed = 38, startDelay = 600): TypewriterResult {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)

  useEffect(() => {
    setDisplayed('')
    setDone(false)
    let i = 0
    let interval: ReturnType<typeof setInterval> | undefined
    const timer = setTimeout(() => {
      interval = setInterval(() => {
        i += 1
        setDisplayed(text.slice(0, i))
        if (i >= text.length) {
          if (interval) clearInterval(interval)
          setDone(true)
        }
      }, speed)
    }, startDelay)
    return () => {
      clearTimeout(timer)
      if (interval) clearInterval(interval)
    }
  }, [text, speed, startDelay])

  return { displayed, done }
}
