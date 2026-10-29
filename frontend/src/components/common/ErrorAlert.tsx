import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from './Button'

interface ErrorAlertProps {
  title?: string
  message: string
  onRetry?: () => void
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
}) => {
  return (
    <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start space-x-3.5 my-4">
      <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1">
        <h4 className="text-sm font-semibold text-rose-900">{title}</h4>
        <p className="text-xs text-rose-700 leading-relaxed">{message}</p>
        {onRetry && (
          <div className="pt-2">
            <Button
              onClick={onRetry}
              variant="outline"
              size="sm"
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              className="bg-white hover:bg-rose-50 text-rose-700 border-rose-300 text-xs py-1"
            >
              Try Again
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
