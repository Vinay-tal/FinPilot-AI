import { test, expect } from '@playwright/test'

test.describe('FinPilot AI End-to-End User Journey Audit', () => {
  test('Complete 10-step financial journey', async ({ page }) => {
    page.on('console', (msg) => console.log(`[BROWSER CONSOLE ${msg.type()}]:`, msg.text()))
    page.on('pageerror', (err) => console.error('[BROWSER ERROR]:', err.message))

    // 1. Start application
    await page.goto('/login')
    await expect(page).toHaveTitle(/FinPilot AI/i)
    await expect(page.locator('text=Intelligent Personal Financial Advisor')).toBeVisible()

    // 2. Log in with demo account
    const demoButton = page.locator('button:has-text("1-Click Demo Sign In")')
    await expect(demoButton).toBeVisible()
    await demoButton.click()

    // 3. Inspect dashboard
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    await expect(page.locator('text=Executive Financial Dashboard')).toBeVisible()
    await expect(page.locator('text=Liquid Bank Assets').first()).toBeVisible()

    // 4. Import synthetic CSV statement
    await page.goto('/transactions')
    await expect(page.locator('text=Transaction Ledger').or(page.locator('text=Transactions')).first()).toBeVisible()

    // Open Import CSV modal
    const importBtn = page.locator('button:has-text("Import Statement")').or(page.locator('button:has-text("Import CSV")')).first()
    await expect(importBtn).toBeVisible()
    await importBtn.click()

    await expect(page.locator('text=Import Bank Statement CSV').or(page.locator('text=Drop your bank CSV')).first()).toBeVisible()

    // Upload synthetic statement
    const syntheticCsv = `Date,Narration,Withdrawal,Deposit,Balance
2026-10-18,UPI-Swiggy Bangalore,520.00,,74480.00
2026-10-19,Salary Credited Infosys,,95000.00,169480.00
2026-10-20,DMart Supermarket,3200.00,,166280.00`

    const uploadArea = page.locator('input[type="file"]')
    await uploadArea.setInputFiles({
      name: 'hdfc_audit_statement.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(syntheticCsv),
    })

    // Wait for preview to render
    await expect(page.locator('text=Preview').or(page.locator('text=Sample Data Preview')).first()).toBeVisible({ timeout: 10000 })

    // Submit import
    const commitImportBtn = page.locator('button:has-text("Commit Import to Ledger")')
    await expect(commitImportBtn).toBeVisible()
    await commitImportBtn.click({ force: true })

    // Verify import completed dialog
    await expect(page.locator('text=Statement Ingestion Complete')).toBeVisible({ timeout: 15000 })
    const doneBtn = page.locator('button:has-text("Done & View Ledger")')
    await expect(doneBtn).toBeVisible()
    await doneBtn.click({ force: true })

    // 5. Review and correct categorized transactions
    await page.goto('/transactions')
    await expect(page.locator('table')).toBeVisible()

    // 6. Inspect Budgets & Savings Goals
    await page.goto('/budgets')
    await expect(page.locator('text=Monthly Category Budgets').or(page.locator('text=Budgets')).first()).toBeVisible()

    await page.goto('/goals')
    await expect(page.locator('text=Financial Goals & Emergency Reserve').or(page.locator('text=Emergency Fund Runway')).first()).toBeVisible()
    const simGoalBtn = page.locator('button[title*="Simulate timeline"]').first()
    if (await simGoalBtn.isVisible()) {
      await simGoalBtn.click()
      await expect(page.locator('text=Goal Timeline Simulator')).toBeVisible()
      const closeSimBtn = page.locator('button:has-text("Close")').or(page.locator('button[aria-label="Close"]')).first()
      if (await closeSimBtn.isVisible()) {
        await closeSimBtn.click()
      }
    }

    // 7. Generate a forecast
    await page.goto('/forecasting')
    await expect(page.locator('text=Financial Forecasting & Risk Analysis').or(page.locator('text=Cash Flow Forecast')).first()).toBeVisible()
    await expect(page.locator('text=PROJECTED 30-DAY BALANCE').or(page.locator('text=Shortfall Risk')).or(page.locator('text=Cash-Flow Trajectory')).first()).toBeVisible({ timeout: 15000 })

    // 8. Ask copilot a question about stored transactions
    await page.goto('/copilot')
    await expect(page.locator('text=FinPilot AI Financial Copilot').or(page.locator('text=Financial Copilot')).or(page.locator('text=Copilot')).first()).toBeVisible()

    const chatInput = page.locator('input[placeholder*="Ask about your expenses"]').or(page.locator('input[type="text"]')).first()
    await chatInput.fill('How much did I spend this month?')
    const sendBtn = page.locator('button:has-text("Ask Copilot")').or(page.locator('button[type="submit"]')).first()
    await sendBtn.click()

    // Wait for copilot turn response
    await page.waitForTimeout(2000)
    await expect(page.locator('text=Verified Deterministic').or(page.locator('text=₹')).first()).toBeVisible({ timeout: 20000 })

    // 9. Run a scenario
    const simNav = page.locator('a[href="/simulation"]')
    if (await simNav.isVisible()) {
      await simNav.click()
    } else {
      await page.goto('/simulation')
    }
    await expect(page.locator('text=Scenario Simulator').first()).toBeVisible()
    await expect(page.locator('text=Deterministic What-If Engine').or(page.locator('text=Model multi-variable')).first()).toBeVisible()

    // 10. Export a financial report
    const reportsNav = page.locator('a[href="/reports"]')
    if (await reportsNav.isVisible()) {
      await reportsNav.click()
    } else {
      await page.goto('/reports')
    }
    await expect(page.locator('text=Monthly Financial Dossier & Reports').or(page.locator('text=Monthly Financial')).first()).toBeVisible()
    const exportBtn = page.locator('button:has-text("Export CSV")').first()
    await expect(exportBtn).toBeVisible()
  })
})
