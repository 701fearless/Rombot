import { Trash2 } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  onCancel: () => void
  onConfirm: () => void
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = '确认删除',
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const panelRef = useRef<HTMLElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const previousActive = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    cancelRef.current?.focus()

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCancel()
        return
      }
      if (event.key !== 'Tab') return
      const buttons = [...(panelRef.current?.querySelectorAll<HTMLButtonElement>('button') ?? [])]
      if (!buttons.length) return
      const first = buttons[0]
      const last = buttons[buttons.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      previousActive?.focus()
    }
  }, [onCancel, open])

  if (!open) return null
  return createPortal(
    <div className='confirm-dialog'>
      <button className='confirm-dialog__backdrop' type='button' aria-label='取消删除' onClick={onCancel} />
      <section
        className='confirm-dialog__panel'
        ref={panelRef}
        role='alertdialog'
        aria-modal='true'
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <span className='confirm-dialog__icon' aria-hidden='true'><Trash2 /></span>
        <div className='confirm-dialog__copy'>
          <span className='eyebrow'>REMOVE FROM LIBRARY</span>
          <h2 id={titleId}>{title}</h2>
          <p id={descriptionId}>{description}</p>
        </div>
        <div className='confirm-dialog__actions'>
          <button ref={cancelRef} type='button' onClick={onCancel}>取消</button>
          <button className='is-danger' type='button' onClick={onConfirm}><Trash2 />{confirmLabel}</button>
        </div>
      </section>
    </div>,
    document.body,
  )
}
