import React, { createContext, useContext, useState, ReactNode } from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info' | 'warning'

interface Toast {
  id: string
  type: ToastType
  message: string
}

interface ToastOptions {
  message: string
  type?: ToastType
  title?: string
}

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void
  showToast: (options: ToastOptions) => void
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = (message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, type, message }])

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }

  const showToast = (options: ToastOptions) => {
    const fullMessage = options.title ? `${options.title}: ${options.message}` : options.message
    addToast(fullMessage, options.type || 'info')
  }

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  return (
    <ToastContext.Provider
      value={{
        toast: addToast,
        showToast,
        success: (msg) => addToast(msg, 'success'),
        error: (msg) => addToast(msg, 'error'),
        info: (msg) => addToast(msg, 'info'),
      }}
    >
      {children}
      {/* Toast container floating at top-right */}
      <div className="fixed top-4 right-4 z-50 flex flex-col space-y-2 max-w-sm pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start space-x-3 p-3.5 rounded-xl shadow-lg border text-sm backdrop-blur-md transition-all duration-200 animate-in slide-in-from-top-2 ${
              t.type === 'success'
                ? 'bg-emerald-950/90 border-emerald-800 text-emerald-100'
                : t.type === 'error'
                ? 'bg-rose-950/90 border-rose-800 text-rose-100'
                : t.type === 'warning'
                ? 'bg-amber-950/90 border-amber-800 text-amber-100'
                : 'bg-navy-900/90 border-navy-700 text-slate-100'
            }`}
          >
            {t.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />}
            {t.type === 'error' && <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />}
            {t.type === 'warning' && <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />}
            {t.type === 'info' && <Info className="w-5 h-5 text-teal-400 shrink-0 mt-0.5" />}
            <p className="flex-1 font-medium leading-tight">{t.message}</p>
            <button
              onClick={() => removeToast(t.id)}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
