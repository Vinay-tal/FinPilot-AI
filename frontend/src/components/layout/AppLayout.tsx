import React, { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export const AppLayout: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  // Format page title from route
  const getPageTitle = () => {
    const path = location.pathname.replace('/', '')
    switch (path) {
      case 'dashboard':
        return 'Financial Executive Dashboard'
      case 'transactions':
        return 'Transaction Explorer & Ledger'
      case 'budgets':
        return 'Monthly Budgets & Pacing'
      case 'goals':
        return 'Financial Goals & Safety Net'
      case 'forecasting':
        return 'Time-Series Cash Flow Forecasting'
      case 'copilot':
        return 'FinPilot AI Financial Copilot'
      case 'insights':
        return 'Financial Insights & Anomaly Detection'
      case 'simulation':
        return 'Scenario Simulator ("What-If" Analysis)'
      case 'reports':
        return 'Financial Reports & Ledger Export'
      case 'settings':
        return 'System Settings & Profile'
      default:
        return 'FinPilot AI'
    }
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative z-10 flex">
            <Sidebar onCloseMobile={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Topbar
          onToggleMobile={() => setMobileOpen(!mobileOpen)}
          pageTitle={getPageTitle()}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
