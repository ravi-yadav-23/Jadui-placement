'use client'

import { useEffect, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'

/** Modal built on the native <dialog> element: focus trap, Esc to close and backdrop come for free. */
export function Dialog({ open, onClose, title, description, children, footer }: {
  open: boolean; onClose: () => void; title: string; description?: string; children?: ReactNode; footer?: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog ref={ref} onClose={onClose} onCancel={onClose}
      className="w-[min(92vw,480px)] rounded-lg border border-border bg-surface p-0 text-fg shadow-pop backdrop:bg-black/40">
      <div className="flex items-start justify-between gap-4 px-5 pt-5">
        <div>
          <h2 className="text-lg">{title}</h2>
          {description && <p className="mt-1 text-sm text-fg-muted">{description}</p>}
        </div>
        <button type="button" onClick={onClose} className="rounded p-1 text-fg-subtle hover:bg-subtle hover:text-fg" aria-label="Close">
          <X className="h-4 w-4" />
        </button>
      </div>
      {children && <div className="px-5 py-4">{children}</div>}
      {footer && <div className="flex justify-end gap-2 border-t border-border px-5 py-3">{footer}</div>}
    </dialog>
  )
}
