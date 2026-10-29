import React from 'react'
import { ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: string
  change?: {
    value: string
    isPositive: boolean
    label?: string
  }
  subtitle?: string
  icon?: React.ReactNode | React.ComponentType<{ className?: string }>
  accentColor?: 'teal' | 'emerald' | 'rose' | 'amber' | 'indigo' | 'slate'
  className?: string
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  subtitle,
  icon,
  accentColor = 'teal',
  className,
}) => {
  const iconBgStyles = {
    teal: 'bg-teal-50 text-teal-600 border-teal-100',
    emerald: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    rose: 'bg-rose-50 text-rose-600 border-rose-100',
    amber: 'bg-amber-50 text-amber-600 border-amber-100',
    indigo: 'bg-indigo-50 text-indigo-600 border-indigo-100',
    slate: 'bg-slate-100 text-slate-600 border-slate-200',
  }

  const renderIcon = () => {
    if (!icon) return null
    if (React.isValidElement(icon)) return icon
    if (typeof icon === 'function' || typeof icon === 'object') {
      const IconComp = icon as React.ComponentType<{ className?: string }>
      return <IconComp className="w-5 h-5" />
    }
    return null
  }

  return (
    <div
      className={cn(
        'bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs hover:shadow-card-hover transition-all duration-200',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
          <h3 className="text-2xl font-bold tracking-tight text-slate-900">{value}</h3>
        </div>
        {icon && (
          <div
            className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center border shadow-xs',
              iconBgStyles[accentColor]
            )}
          >
            {renderIcon()}
          </div>
        )}
      </div>

      {(change || subtitle) && (
        <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          {change ? (
            <div className="flex items-center space-x-1">
              <span
                className={cn(
                  'inline-flex items-center font-semibold px-1.5 py-0.5 rounded text-[11px]',
                  change.isPositive
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-rose-50 text-rose-700'
                )}
              >
                {change.isPositive ? (
                  <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                ) : (
                  <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
                )}
                {change.value}
              </span>
              {change.label && <span className="text-slate-400">{change.label}</span>}
            </div>
          ) : (
            <div />
          )}

          {subtitle && <span className="text-slate-500 font-medium">{subtitle}</span>}
        </div>
      )}
    </div>
  )
}
