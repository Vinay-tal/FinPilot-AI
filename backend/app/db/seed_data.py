import uuid
import hashlib
from datetime import date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.account import FinancialAccount
from app.models.category import TransactionCategory
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import SavingsGoal
from app.models.recurring_transaction import RecurringTransaction
from app.models.financial_insight import FinancialInsight
from app.core.security import hash_password
from app.core.config import settings
from app.services.transaction_service import compute_fingerprint

SYSTEM_CATEGORIES = [
    # Income
    {"name": "Salary", "slug": "salary", "icon": "wallet", "color": "#10b981", "is_income": True},
    {"name": "Freelance & Consulting", "slug": "freelance", "icon": "briefcase", "color": "#059669", "is_income": True},
    {"name": "Investment Returns", "slug": "investment-returns", "icon": "trending-up", "color": "#14b8a6", "is_income": True},
    {"name": "Refunds & Cashback", "slug": "refunds-cashback", "icon": "rotate-ccw", "color": "#06b6d4", "is_income": True},
    # Expenses
    {"name": "Housing & Rent", "slug": "housing-rent", "icon": "home", "color": "#f43f5e", "is_income": False},
    {"name": "Food & Dining", "slug": "food-dining", "icon": "utensils", "color": "#f97316", "is_income": False},
    {"name": "Groceries & Essentials", "slug": "groceries-essentials", "icon": "shopping-bag", "color": "#84cc16", "is_income": False},
    {"name": "Utilities & Bills", "slug": "utilities-bills", "icon": "zap", "color": "#eab308", "is_income": False},
    {"name": "Transportation & Fuel", "slug": "transportation-fuel", "icon": "car", "color": "#3b82f6", "is_income": False},
    {"name": "Shopping & Lifestyle", "slug": "shopping-lifestyle", "icon": "shopping-cart", "color": "#ec4899", "is_income": False},
    {"name": "Entertainment & OTT", "slug": "entertainment-ott", "icon": "tv", "color": "#8b5cf6", "is_income": False},
    {"name": "Subscriptions & Memberships", "slug": "subscriptions", "icon": "repeat", "color": "#a855f7", "is_income": False},
    {"name": "Education & Learning", "slug": "education", "icon": "book-open", "color": "#0284c7", "is_income": False},
    {"name": "Transfers & Remittance", "slug": "transfers", "icon": "arrow-left-right", "color": "#64748b", "is_income": False},
    {"name": "Bank Fees & Charges", "slug": "fees-charges", "icon": "alert-circle", "color": "#dc2626", "is_income": False},
    {"name": "Investments & SIP", "slug": "investments-sip", "icon": "piggy-bank", "color": "#6366f1", "is_income": False},
    {"name": "Health & Fitness", "slug": "health-fitness", "icon": "activity", "color": "#06b6d4", "is_income": False},
    {"name": "Miscellaneous", "slug": "miscellaneous", "icon": "more-horizontal", "color": "#64748b", "is_income": False},
]

def seed_system_categories(db: Session) -> Dict[str, TransactionCategory]:
    """Ensure standard Indian system categories exist and return category map."""
    cat_map = {}
    for cat_data in SYSTEM_CATEGORIES:
        cat = db.query(TransactionCategory).filter(
            TransactionCategory.slug == cat_data["slug"],
            TransactionCategory.is_system == True
        ).first()
        if not cat:
            cat = TransactionCategory(
                name=cat_data["name"],
                slug=cat_data["slug"],
                icon=cat_data["icon"],
                color=cat_data["color"],
                is_income=cat_data["is_income"],
                is_system=True,
                user_id=None,
            )
            db.add(cat)
            db.flush()
        cat_map[cat.slug] = cat
    return cat_map

def seed_demo_data(db: Session) -> User:
    """Seed comprehensive synthetic Indian financial history for Rahul Sharma."""
    # 1. System categories
    cat_map = seed_system_categories(db)

    # 2. Check if demo user already exists
    demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL.lower()).first()
    if not demo_user:
        demo_user = User(
            email=settings.DEMO_USER_EMAIL.lower(),
            password_hash=hash_password(settings.DEMO_USER_PASSWORD),
            full_name=settings.DEMO_USER_NAME,
            currency=settings.DEMO_USER_CURRENCY,
            is_active=True,
            is_demo=True,
        )
        db.add(demo_user)
        db.flush()

    # 3. Create or get Accounts
    hdfc_acct = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == demo_user.id,
        FinancialAccount.name == "HDFC Salary Savings A/C"
    ).first()
    if not hdfc_acct:
        hdfc_acct = FinancialAccount(
            user_id=demo_user.id,
            name="HDFC Salary Savings A/C",
            account_type="SAVINGS",
            institution="HDFC Bank",
            account_number_mask="*4821",
            balance_paise=18450000,  # ₹1,84,500.00
            currency="INR",
            is_active=True,
        )
        db.add(hdfc_acct)

    icici_card = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == demo_user.id,
        FinancialAccount.name == "ICICI Coral Credit Card"
    ).first()
    if not icici_card:
        icici_card = FinancialAccount(
            user_id=demo_user.id,
            name="ICICI Coral Credit Card",
            account_type="CREDIT_CARD",
            institution="ICICI Bank",
            account_number_mask="*9012",
            balance_paise=1420000,  # ₹14,200.00
            currency="INR",
            is_active=True,
        )
        db.add(icici_card)

    zerodha_acct = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == demo_user.id,
        FinancialAccount.name == "Zerodha Demat & Trading"
    ).first()
    if not zerodha_acct:
        zerodha_acct = FinancialAccount(
            user_id=demo_user.id,
            name="Zerodha Demat & Trading",
            account_type="INVESTMENT",
            institution="Zerodha",
            account_number_mask="*7732",
            balance_paise=35000000,  # ₹3,50,000.00
            currency="INR",
            is_active=True,
        )
        db.add(zerodha_acct)

    db.flush()

    # 4. Generate 12 months of transactions if not already populated
    today = date.today()
    existing_tx_count = db.query(Transaction).filter(Transaction.user_id == demo_user.id).count()
    if existing_tx_count < 50:
        # Seed 12 months back
        transactions_to_add = []

        for m_offset in range(11, -1, -1):
            # Compute month base date
            year = today.year
            month = today.month - m_offset
            while month <= 0:
                month += 12
                year -= 1

            # 1. Salary Credit (30th or 28th)
            salary_day = 28 if month == 2 else 30
            salary_dt = date(year, month, salary_day)
            salary_tx = Transaction(
                user_id=demo_user.id,
                account_id=hdfc_acct.id,
                category_id=cat_map["salary"].id,
                date=salary_dt,
                amount_paise=12500000,  # ₹1,25,000.00
                transaction_type="CREDIT",
                narration=f"ACH CR-INFOSYS TECH LTD-SALARY-{salary_dt.strftime('%b%y').upper()}",
                raw_narration=f"ACH CR-INFOSYS TECH LTD-SALARY-{salary_dt.strftime('%b%y').upper()}-HDFC000182",
                merchant_name="Infosys Technologies Ltd",
                payment_mode="NET_BANKING",
                reference_id=f"INF{year}{month:02d}SAL",
                fingerprint=compute_fingerprint(demo_user.id, salary_dt, 12500000, "CREDIT", f"ACH CR-INFOSYS TECH LTD-SALARY-{salary_dt.strftime('%b%y').upper()}"),
                categorization_method="RULE",
                categorization_confidence=1.0,
            )
            transactions_to_add.append(salary_tx)

            # 2. Rent Debit via UPI (1st)
            rent_dt = date(year, month, 1)
            rent_tx = Transaction(
                user_id=demo_user.id,
                account_id=hdfc_acct.id,
                category_id=cat_map["housing-rent"].id,
                date=rent_dt,
                amount_paise=2800000,  # ₹28,000.00
                transaction_type="DEBIT",
                narration="UPI/428192837/Ramesh Landlord Rent/HDFC",
                raw_narration="UPI/428192837/Ramesh Landlord Rent/HDFC/428192837192",
                merchant_name="Ramesh Landlord",
                payment_mode="UPI",
                reference_id=f"UPI{year}{month:02d}RENT",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, rent_dt, 2800000, "DEBIT", "UPI/428192837/Ramesh Landlord Rent/HDFC"),
                categorization_method="RULE",
                categorization_confidence=1.0,
            )
            transactions_to_add.append(rent_tx)

            # 3. Zerodha SIP Investment (5th)
            sip_dt = date(year, month, 5)
            sip_tx = Transaction(
                user_id=demo_user.id,
                account_id=hdfc_acct.id,
                category_id=cat_map["investments-sip"].id,
                date=sip_dt,
                amount_paise=2500000,  # ₹25,000.00
                transaction_type="DEBIT",
                narration="ACH DR-ZERODHA BROKING-MF-SIP",
                raw_narration="ACH DR-ZERODHA BROKING-MF-SIP-NACH428192",
                merchant_name="Zerodha Broking",
                payment_mode="NET_BANKING",
                reference_id=f"NACH{year}{month:02d}SIP",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, sip_dt, 2500000, "DEBIT", "ACH DR-ZERODHA BROKING-MF-SIP"),
                categorization_method="RULE",
                categorization_confidence=1.0,
            )
            transactions_to_add.append(sip_tx)

            # 4. Utilities: BESCOM, ACT Fibernet, Airtel
            util_dt_1 = date(year, month, 8)
            transactions_to_add.append(Transaction(
                user_id=demo_user.id,
                account_id=hdfc_acct.id,
                category_id=cat_map["utilities-bills"].id,
                date=util_dt_1,
                amount_paise=185000,  # ₹1,850.00
                transaction_type="DEBIT",
                narration="BESCOM Electricity Bill Bangalore",
                merchant_name="BESCOM",
                payment_mode="UPI",
                reference_id=f"BES{year}{month:02d}",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, util_dt_1, 185000, "DEBIT", "BESCOM Electricity Bill Bangalore"),
                categorization_method="RULE",
                categorization_confidence=0.98,
            ))

            util_dt_2 = date(year, month, 10)
            transactions_to_add.append(Transaction(
                user_id=demo_user.id,
                account_id=hdfc_acct.id,
                category_id=cat_map["utilities-bills"].id,
                date=util_dt_2,
                amount_paise=117900,  # ₹1,179.00
                transaction_type="DEBIT",
                narration="ACT Fibernet Broadband Bill",
                merchant_name="ACT Fibernet",
                payment_mode="UPI",
                reference_id=f"ACT{year}{month:02d}",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, util_dt_2, 117900, "DEBIT", "ACT Fibernet Broadband Bill"),
                categorization_method="RULE",
                categorization_confidence=0.99,
            ))

            util_dt_3 = date(year, month, 12)
            transactions_to_add.append(Transaction(
                user_id=demo_user.id,
                account_id=hdfc_acct.id,
                category_id=cat_map["utilities-bills"].id,
                date=util_dt_3,
                amount_paise=99900,  # ₹999.00
                transaction_type="DEBIT",
                narration="Airtel Postpaid 5G Family Plan",
                merchant_name="Airtel",
                payment_mode="UPI",
                reference_id=f"AIR{year}{month:02d}",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, util_dt_3, 99900, "DEBIT", "Airtel Postpaid 5G Family Plan"),
                categorization_method="RULE",
                categorization_confidence=0.99,
            ))

            # 5. Subscriptions: Netflix, Spotify, Cult.fit
            sub_dt = date(year, month, 15)
            transactions_to_add.append(Transaction(
                user_id=demo_user.id,
                account_id=icici_card.id,
                category_id=cat_map["entertainment-ott"].id,
                date=sub_dt,
                amount_paise=64900,  # ₹649.00
                transaction_type="DEBIT",
                narration="Netflix Entertainment India Monthly",
                merchant_name="Netflix",
                payment_mode="CREDIT_CARD",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, sub_dt, 64900, "DEBIT", "Netflix Entertainment India Monthly"),
                categorization_method="RULE",
                categorization_confidence=1.0,
            ))

            transactions_to_add.append(Transaction(
                user_id=demo_user.id,
                account_id=icici_card.id,
                category_id=cat_map["entertainment-ott"].id,
                date=sub_dt,
                amount_paise=17900,  # ₹179.00
                transaction_type="DEBIT",
                narration="Spotify AB India Family Premium",
                merchant_name="Spotify",
                payment_mode="CREDIT_CARD",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, sub_dt, 17900, "DEBIT", "Spotify AB India Family Premium"),
                categorization_method="RULE",
                categorization_confidence=1.0,
            ))

            transactions_to_add.append(Transaction(
                user_id=demo_user.id,
                account_id=hdfc_acct.id,
                category_id=cat_map["health-fitness"].id,
                date=sub_dt,
                amount_paise=149900,  # ₹1,499.00
                transaction_type="DEBIT",
                narration="Cult.fit Fitness Membership Pass",
                merchant_name="Cult.fit",
                payment_mode="UPI",
                is_recurring=True,
                fingerprint=compute_fingerprint(demo_user.id, sub_dt, 149900, "DEBIT", "Cult.fit Fitness Membership Pass"),
                categorization_method="RULE",
                categorization_confidence=0.98,
            ))

            # 6. Groceries & Essentials (Blinkit, Zepto, D-Mart)
            for d, merchant, amt, desc in [
                (3, "Blinkit", 48500, "Blinkit Koramangala Daily Essentials"),
                (9, "Zepto", 62000, "Zepto Quick Commerce Vegetables & Dairy"),
                (16, "D-Mart", 385000, "D-Mart Bellandur Monthly Grocery Run"),
                (22, "Blinkit", 54000, "Blinkit Snacks & Beverages"),
                (27, "Zepto", 41000, "Zepto Fruits and Breakfast Supplies"),
            ]:
                if d <= 28:
                    g_dt = date(year, month, d)
                    transactions_to_add.append(Transaction(
                        user_id=demo_user.id,
                        account_id=hdfc_acct.id,
                        category_id=cat_map["groceries-essentials"].id,
                        date=g_dt,
                        amount_paise=amt,
                        transaction_type="DEBIT",
                        narration=desc,
                        merchant_name=merchant,
                        payment_mode="UPI",
                        fingerprint=compute_fingerprint(demo_user.id, g_dt, amt, "DEBIT", desc),
                        categorization_method="RULE",
                        categorization_confidence=0.97,
                    ))

            # 7. Food & Dining (Swiggy, Zomato, Cafes)
            for d, merchant, amt, desc in [
                (2, "Swiggy", 45000, "Swiggy Biryani Dinner Indiranagar"),
                (6, "Chai Point", 18000, "Chai Point Afternoon Tea & Samosa"),
                (11, "Zomato", 68000, "Zomato Gourmet Weekend Pizza"),
                (14, "Third Wave Coffee", 34000, "Third Wave Coffee Koramangala"),
                (19, "Swiggy", 52000, "Swiggy Healthy Bowl Lunch"),
                (21, "Toit Brewpub", 245000, "Toit Brewpub Team Dinner Bangalore"),
                (25, "Zomato", 58000, "Zomato North Indian Dinner"),
            ]:
                if d <= 28:
                    f_dt = date(year, month, d)
                    transactions_to_add.append(Transaction(
                        user_id=demo_user.id,
                        account_id=hdfc_acct.id,
                        category_id=cat_map["food-dining"].id,
                        date=f_dt,
                        amount_paise=amt,
                        transaction_type="DEBIT",
                        narration=desc,
                        merchant_name=merchant,
                        payment_mode="UPI",
                        fingerprint=compute_fingerprint(demo_user.id, f_dt, amt, "DEBIT", desc),
                        categorization_method="RULE",
                        categorization_confidence=0.98,
                    ))

            # 8. Commute (Uber, Rapido, Metro)
            for d, merchant, amt, desc in [
                (4, "Uber", 32000, "Uber Premier Ride to Tech Park"),
                (7, "Rapido", 11000, "Rapido Bike Taxi Commute"),
                (13, "Namma Metro", 20000, "Namma Metro Smart Card Auto-Topup"),
                (17, "Uber", 29000, "Uber Go Airport Road Commute"),
                (23, "Rapido", 9500, "Rapido Bike Taxi Quick Ride"),
                (26, "Uber", 41000, "Uber Ride Indiranagar to HSR"),
            ]:
                if d <= 28:
                    c_dt = date(year, month, d)
                    transactions_to_add.append(Transaction(
                        user_id=demo_user.id,
                        account_id=hdfc_acct.id,
                        category_id=cat_map["transportation-fuel"].id,
                        date=c_dt,
                        amount_paise=amt,
                        transaction_type="DEBIT",
                        narration=desc,
                        merchant_name=merchant,
                        payment_mode="UPI",
                        fingerprint=compute_fingerprint(demo_user.id, c_dt, amt, "DEBIT", desc),
                        categorization_method="RULE",
                        categorization_confidence=0.96,
                    ))

            # 9. Shopping & Lifestyle (Amazon, Myntra, Flipkart)
            for d, merchant, amt, desc in [
                (10, "Amazon India", 189900, "Amazon India Electronics & Books"),
                (18, "Myntra", 249900, "Myntra Casual Apparel Sale"),
            ]:
                if d <= 28:
                    s_dt = date(year, month, d)
                    transactions_to_add.append(Transaction(
                        user_id=demo_user.id,
                        account_id=icici_card.id,
                        category_id=cat_map["shopping-lifestyle"].id,
                        date=s_dt,
                        amount_paise=amt,
                        transaction_type="DEBIT",
                        narration=desc,
                        merchant_name=merchant,
                        payment_mode="CREDIT_CARD",
                        fingerprint=compute_fingerprint(demo_user.id, s_dt, amt, "DEBIT", desc),
                        categorization_method="RULE",
                        categorization_confidence=0.97,
                    ))

            # 10. Occasional refund
            if month in (3, 7, 10):
                ref_dt = date(year, month, 15)
                transactions_to_add.append(Transaction(
                    user_id=demo_user.id,
                    account_id=hdfc_acct.id,
                    category_id=cat_map["refunds-cashback"].id,
                    date=ref_dt,
                    amount_paise=45000,  # ₹450.00
                    transaction_type="CREDIT",
                    narration="UPI/REFUND/SWIGGY FOOD ORDER CANCELLED",
                    merchant_name="Swiggy",
                    payment_mode="UPI",
                    fingerprint=compute_fingerprint(demo_user.id, ref_dt, 45000, "CREDIT", "UPI/REFUND/SWIGGY FOOD ORDER CANCELLED"),
                    categorization_method="RULE",
                    categorization_confidence=0.99,
                ))

        db.add_all(transactions_to_add)
        db.flush()

    # 5. Seed Budgets for current month and previous month
    cur_month = today.month
    cur_year = today.year
    budget_allocations = [
        ("food-dining", 1500000),      # ₹15,000.00
        ("groceries-essentials", 1200000),  # ₹12,000.00
        ("housing-rent", 2800000),     # ₹28,000.00
        ("utilities-bills", 500000),   # ₹5,000.00
        ("transportation-fuel", 600000), # ₹6,000.00
        ("shopping-lifestyle", 1000000), # ₹10,000.00
    ]
    for slug, amt in budget_allocations:
        cat = cat_map.get(slug)
        if cat:
            existing_b = db.query(Budget).filter(
                Budget.user_id == demo_user.id,
                Budget.category_id == cat.id,
                Budget.month == cur_month,
                Budget.year == cur_year,
            ).first()
            if not existing_b:
                db.add(Budget(
                    user_id=demo_user.id,
                    category_id=cat.id,
                    month=cur_month,
                    year=cur_year,
                    amount_paise=amt,
                    alert_threshold=0.80,
                ))

    # 6. Seed Recurring Transactions
    recurring_items = [
        ("Ramesh Landlord Rent", "Ramesh Landlord", 2800000, "MONTHLY", "housing-rent"),
        ("Zerodha SIP", "Zerodha Broking", 2500000, "MONTHLY", "investments-sip"),
        ("BESCOM Bill", "BESCOM", 185000, "MONTHLY", "utilities-bills"),
        ("ACT Fibernet", "ACT Fibernet", 117900, "MONTHLY", "utilities-bills"),
        ("Netflix India", "Netflix", 64900, "MONTHLY", "entertainment-ott"),
        ("Spotify Premium", "Spotify", 17900, "MONTHLY", "entertainment-ott"),
    ]
    for name, merchant, amt, freq, slug in recurring_items:
        cat = cat_map.get(slug)
        if cat:
            existing_r = db.query(RecurringTransaction).filter(
                RecurringTransaction.user_id == demo_user.id,
                RecurringTransaction.name == name,
            ).first()
            if not existing_r:
                db.add(RecurringTransaction(
                    user_id=demo_user.id,
                    category_id=cat.id,
                    name=name,
                    merchant_name=merchant,
                    expected_amount_paise=amt,
                    frequency=freq,
                    last_detected_date=today - timedelta(days=20),
                    next_expected_date=today + timedelta(days=10),
                    is_active=True,
                ))

    # 7. Seed Savings Goals
    goals_data = [
        {
            "name": "6-Month Emergency Fund",
            "target_amount_paise": 30000000,  # ₹3,00,000.00
            "current_amount_paise": 18450000,  # ₹1,84,500.00
            "target_date": date(2026, 12, 31),
            "category": "EMERGENCY_FUND",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
        },
        {
            "name": "Goa Year-End Vacation",
            "target_amount_paise": 4500000,   # ₹45,000.00
            "current_amount_paise": 3200000,   # ₹32,000.00
            "target_date": date(2026, 11, 30),
            "category": "VACATION",
            "priority": "MEDIUM",
            "status": "IN_PROGRESS",
        },
    ]
    for g_info in goals_data:
        existing_g = db.query(SavingsGoal).filter(
            SavingsGoal.user_id == demo_user.id,
            SavingsGoal.name == g_info["name"],
        ).first()
        if not existing_g:
            db.add(SavingsGoal(
                user_id=demo_user.id,
                name=g_info["name"],
                target_amount_paise=g_info["target_amount_paise"],
                current_amount_paise=g_info["current_amount_paise"],
                target_date=g_info["target_date"],
                category=g_info["category"],
                priority=g_info["priority"],
                status=g_info["status"],
            ))

    # 8. Seed Financial Insights & Anomaly Alerts
    insights_data = [
        {
            "insight_type": "ANOMALY",
            "severity": "WARNING",
            "title": "Unusual Dining Out Bill: Toit Brewpub (₹2,450.00)",
            "description": "This transaction is 2.8x higher than your average dining bill of ₹870.00 in Bangalore.",
            "metadata_json": '{"category": "Food & Dining", "amount": 2450.0, "z_score": 2.8}',
        },
        {
            "insight_type": "SPENDING_SPIKE",
            "severity": "INFO",
            "title": "Weekend Quick-Commerce Spike (Blinkit + Zepto)",
            "description": "Quick commerce grocery spending rose by 34% this weekend compared to your 30-day rolling baseline.",
            "metadata_json": '{"delta_pct": 34.0, "spend_inr": 1560.0}',
        },
        {
            "insight_type": "BUDGET_ALERT",
            "severity": "WARNING",
            "title": "Food & Dining Budget at 85% Utilization",
            "description": "You have consumed ₹12,750 of your ₹15,000 budget with 10 days remaining in the month.",
            "metadata_json": '{"budget_pct": 85.0, "remaining_inr": 2250.0}',
        },
        {
            "insight_type": "SAVINGS_TIP",
            "severity": "INFO",
            "title": "SIP Discipline Milestone: 12-Month Streak",
            "description": "You have consistently transferred ₹25,000/month into mutual fund SIPs for 12 consecutive months.",
            "metadata_json": '{"streak_months": 12, "total_invested": 300000.0}',
        },
    ]
    for ins in insights_data:
        existing_ins = db.query(FinancialInsight).filter(
            FinancialInsight.user_id == demo_user.id,
            FinancialInsight.title == ins["title"],
        ).first()
        if not existing_ins:
            db.add(FinancialInsight(
                user_id=demo_user.id,
                insight_type=ins["insight_type"],
                severity=ins["severity"],
                title=ins["title"],
                description=ins["description"],
                metadata_json=ins["metadata_json"],
                is_read=False,
                is_resolved=False,
            ))

    db.commit()
    return demo_user
