import { describe, it, expect } from 'vitest'
import { formatINR, formatDate, formatDateIST, formatPercent } from '@/lib/formatters'

describe('formatters', () => {
  it('formats standard INR amounts with commas according to Indian numbering system', () => {
    const formatted = formatINR(125000)
    expect(formatted).toContain('1,25,000')
    expect(formatted).toContain('₹')
  })

  it('formats negative INR amounts cleanly with leading minus', () => {
    const formatted = formatINR(-45000)
    expect(formatted).toContain('-')
    expect(formatted).toContain('45,000')
  })

  it('formats compact Lakhs when compact option is true', () => {
    expect(formatINR(1250000, { compact: true })).toBe('₹12.50 L')
  })

  it('formats compact Crores when amount is 10,000,000 or higher', () => {
    expect(formatINR(15000000, { compact: true })).toBe('₹1.50 Cr')
  })

  it('formats percentages correctly', () => {
    expect(formatPercent(42.06)).toBe('42.1%')
    expect(formatPercent(0)).toBe('0.0%')
  })

  it('formats date and date IST without crashing', () => {
    const formatted = formatDate('2026-10-22')
    expect(formatted).toBeTruthy()

    const formattedIST = formatDateIST('2026-10-22T10:30:00Z')
    expect(formattedIST).toBeTruthy()
  })
})
