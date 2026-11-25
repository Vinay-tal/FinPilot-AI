/**
 * Indian Rupee (INR ₹) and date formatting helpers for FinPilot AI
 */

export function formatINR(
  amount: number,
  options?: { showSign?: boolean; compact?: boolean; hideDecimals?: boolean }
): string {
  const { showSign = false, compact = false, hideDecimals = false } = options || {}

  if (compact && Math.abs(amount) >= 10000000) {
    // Crores
    const cr = (amount / 10000000).toFixed(2)
    return `₹${cr} Cr`
  }
  if (compact && Math.abs(amount) >= 100000) {
    // Lakhs
    const lk = (amount / 100000).toFixed(2)
    return `₹${lk} L`
  }

  const sign = showSign && amount > 0 ? '+' : ''
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: hideDecimals ? 0 : 2,
    maximumFractionDigits: hideDecimals ? 0 : 2,
  }).format(Math.abs(amount))

  if (amount < 0) {
    return `-${formatted}`
  }
  return `${sign}${formatted}`
}

export function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function formatDateIST(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

export function formatPercent(val: number): string {
  return `${val.toFixed(1)}%`
}
