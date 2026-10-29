import React from 'react'
import { FolderOpen } from 'lucide-react'
import { Button } from './Button'

interface EmptyStateProps {
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ReactNode | React.ComponentType<{ className?: string }>
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon,
}) => {
  const renderIcon = () => {
    if (!icon) return <FolderOpen className="w-6 h-6 text-slate-400" />
    if (React.isValidElement(icon)) return icon
    if (typeof icon === 'function' || typeof icon === 'object') {
      const IconComponent = icon as React.ComponentType<{ className?: string }>
      return <IconComponent className="w-6 h-6 text-slate-400" />
    }
    return <FolderOpen className="w-6 h-6 text-slate-400" />
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-white rounded-xl border border-dashed border-slate-300">
      <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mb-3.5 shadow-xs">
        {renderIcon()}
      </div>
      <h3 className="text-base font-semibold text-slate-800">{title}</h3>
      <p className="text-xs text-slate-500 max-w-sm mt-1 mb-5">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} size="sm">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
