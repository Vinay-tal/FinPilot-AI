from fastapi.testclient import TestClient
from app.db.seed_data import seed_demo_data
from app.models.transaction import Transaction
from app.models.account import FinancialAccount
from app.models.budget import Budget
from app.models.recurring_transaction import RecurringTransaction
from app.models.goal import SavingsGoal

def test_seed_demo_data_integrity(db_session):
    """Verify that Rahul Sharma demo dataset populates 12 months of realistic Indian data."""
    demo_user = seed_demo_data(db_session)
    assert demo_user.email == "demo@finpilot.in"
    assert demo_user.full_name == "Rahul Sharma"
    assert demo_user.is_demo is True

    # Accounts
    accounts = db_session.query(FinancialAccount).filter(FinancialAccount.user_id == demo_user.id).all()
    assert len(accounts) == 3
    acct_names = [a.name for a in accounts]
    assert "HDFC Salary Savings A/C" in acct_names
    assert "ICICI Coral Credit Card" in acct_names
    assert "Zerodha Demat & Trading" in acct_names

    # Transactions count across 12 months
    tx_count = db_session.query(Transaction).filter(Transaction.user_id == demo_user.id).count()
    assert tx_count > 250, f"Expected >250 transactions, got {tx_count}"

    # Verify transaction variety (UPI, Netbanking, Card)
    upi_count = db_session.query(Transaction).filter(
        Transaction.user_id == demo_user.id,
        Transaction.payment_mode == "UPI"
    ).count()
    assert upi_count > 100

    # Budgets
    budgets = db_session.query(Budget).filter(Budget.user_id == demo_user.id).all()
    assert len(budgets) >= 6

    # Recurring
    recurring = db_session.query(RecurringTransaction).filter(RecurringTransaction.user_id == demo_user.id).all()
    assert len(recurring) >= 5

    # Goals
    goals = db_session.query(SavingsGoal).filter(SavingsGoal.user_id == demo_user.id).all()
    assert len(goals) == 2
