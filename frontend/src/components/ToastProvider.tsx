import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import type { PropsWithChildren } from 'react'

interface ToastApi {
  show: (message: string) => void
}

const ToastContext = createContext<ToastApi | null>(null)

export function ToastProvider({ children }: PropsWithChildren) {
  const [message, setMessage] = useState('')
  const timer = useRef<number | null>(null)
  const show = useCallback((next: string) => {
    setMessage(next)
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setMessage(''), 2600)
  }, [])
  const api = useMemo(() => ({ show }), [show])
  return (
    <ToastContext.Provider value={api}>
      {children}
      {message && <div className='app-toast' role='status'>{message}</div>}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const value = useContext(ToastContext)
  if (!value) throw new Error('useToast must be used inside ToastProvider')
  return value
}
