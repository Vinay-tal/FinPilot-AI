import React from 'react'
import { cn } from '@/lib/utils'

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => {
  return <div className={cn('animate-pulse bg-slate-200/80 rounded-md', className)} />
}

export const CardSkeleton: React.FC<{ count?: number; className?: string }> = ({ count = 1, className }) => {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="bg-white rounded-xl p-5 border border-slate-200/80 space-y-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-8 w-44" />
          <div className="pt-2 flex justify-between">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      ))}
    </div>
  )
}

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center space-x-4 p-3 bg-white border border-slate-100 rounded-lg">
          <Skeleton className="h-9 w-9 rounded-full shrink-0" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-28" />
          </div>
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      ))}
    </div>
  )
}
