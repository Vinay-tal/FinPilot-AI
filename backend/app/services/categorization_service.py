import re
import uuid
from typing import Dict, Any, Optional, Tuple, List, Union
from sqlalchemy.orm import Session
from app.models.category import TransactionCategory
from app.models.transaction import Transaction
from app.ml.classifier import get_transaction_classifier
from app.core.exceptions import NotFoundException, ForbiddenException

# Canonical merchant mapping regex patterns
MERCHANT_PATTERNS: List[Tuple[str, str, str]] = [
    # (regex_pattern, canonical_merchant, category_slug)
    (r"\b(swiggy|bundl\s*tech)\b", "Swiggy", "food-dining"),
    (r"\b(zomato)\b", "Zomato", "food-dining"),
    (r"\b(starbucks|tata\s*starbucks)\b", "Starbucks", "food-dining"),
    (r"\b(third\s*wave\s*coffee)\b", "Third Wave Coffee", "food-dining"),
    (r"\b(mcdonald|hardcastle)\b", "McDonald's", "food-dining"),
    (r"\b(domino'?s|jubilant\s*food)\b", "Domino's Pizza", "food-dining"),
    (r"\b(behrouz|faasos|rebel\s*foods)\b", "Rebel Foods", "food-dining"),
    (r"\b(chai\s*point|chaayos)\b", "Chai Point", "food-dining"),
    (r"\b(haldiram)\b", "Haldiram's", "food-dining"),
    (r"\b(burger\s*king)\b", "Burger King", "food-dining"),
    (r"\b(kfc|pizza\s*hut)\b", "Yum! Restaurants", "food-dining"),

    # Groceries
    (r"\b(zepto)\b", "Zepto", "groceries-essentials"),
    (r"\b(blinkit|grofers)\b", "Blinkit", "groceries-essentials"),
    (r"\b(instamart)\b", "Swiggy Instamart", "groceries-essentials"),
    (r"\b(bigbasket|innovative\s*retail)\b", "BigBasket", "groceries-essentials"),
    (r"\b(dmart|avenue\s*supermarts)\b", "DMart", "groceries-essentials"),
    (r"\b(nature'?s\s*basket)\b", "Nature's Basket", "groceries-essentials"),
    (r"\b(country\s*delight)\b", "Country Delight", "groceries-essentials"),
    (r"\b(spencer'?s)\b", "Spencer's", "groceries-essentials"),
    (r"\b(more\s*retail|reliance\s*fresh)\b", "Reliance Fresh", "groceries-essentials"),

    # Transport & Fuel
    (r"\b(uber)\b", "Uber", "transportation-fuel"),
    (r"\b(ola\s*cabs|ani\s*tech)\b", "Ola Cabs", "transportation-fuel"),
    (r"\b(rapido|roopena)\b", "Rapido", "transportation-fuel"),
    (r"\b(namma\s*metro|bmrc|dmrc)\b", "Metro Transit", "transportation-fuel"),
    (r"\b(irctc)\b", "IRCTC", "transportation-fuel"),
    (r"\b(indigo|interglobe)\b", "IndiGo Airlines", "transportation-fuel"),
    (r"\b(air\s*india)\b", "Air India", "transportation-fuel"),
    (r"\b(makemytrip|mmt|goibibo)\b", "MakeMyTrip", "transportation-fuel"),
    (r"\b(indian\s*oil|ioc|iocl)\b", "Indian Oil", "transportation-fuel"),
    (r"\b(bharat\s*petroleum|bpcl)\b", "Bharat Petroleum", "transportation-fuel"),
    (r"\b(hindustan\s*petroleum|hpcl)\b", "Hindustan Petroleum", "transportation-fuel"),
    (r"\b(shell\s*fuel|shell\s*india)\b", "Shell", "transportation-fuel"),
    (r"\b(fastag|netc|ihmcl)\b", "FASTag Toll", "transportation-fuel"),
    (r"\b(blusmart)\b", "BluSmart", "transportation-fuel"),

    # Housing & Rent
    (r"\b(nobroker)\b", "NoBroker", "housing-rent"),
    (r"\b(cred\s*rentpay|rentpay)\b", "CRED RentPay", "housing-rent"),
    (r"\b(mygate)\b", "MyGate", "housing-rent"),
    (r"\b(apartment\s*maintenance|society\s*dues|owners\s*assoc)\b", "Apartment Society", "housing-rent"),
    (r"\b(flat\s*rent|house\s*rent|landlord)\b", "House Rent", "housing-rent"),

    # Utilities & Bills
    (r"\b(bescom|tata\s*power|bses|mahavitaran)\b", "Electricity Board", "utilities-bills"),
    (r"\b(bwssb|delhi\s*jal\s*board|water\s*board)\b", "Water Board", "utilities-bills"),
    (r"\b(igl|mgl|indraprastha\s*gas|mahanagar\s*gas)\b", "Piped Natural Gas", "utilities-bills"),
    (r"\b(bharat\s*gas|indane|hp\s*gas|cylinder)\b", "LPG Gas Refill", "utilities-bills"),
    (r"\b(airtel|bharti\s*airtel)\b", "Airtel", "utilities-bills"),
    (r"\b(jio|reliance\s*jio)\b", "Reliance Jio", "utilities-bills"),
    (r"\b(act\s*corp|act\s*fibernet)\b", "ACT Fibernet", "utilities-bills"),
    (r"\b(tata\s*play|dish\s*tv|dth)\b", "DTH Service", "utilities-bills"),

    # Shopping
    (r"\b(amazon|amzn)\b", "Amazon", "shopping-lifestyle"),
    (r"\b(flipkart)\b", "Flipkart", "shopping-lifestyle"),
    (r"\b(myntra)\b", "Myntra", "shopping-lifestyle"),
    (r"\b(ajio)\b", "Ajio", "shopping-lifestyle"),
    (r"\b(nykaa)\b", "Nykaa", "shopping-lifestyle"),
    (r"\b(croma|infiniti\s*retail)\b", "Croma", "shopping-lifestyle"),
    (r"\b(reliance\s*digital)\b", "Reliance Digital", "shopping-lifestyle"),
    (r"\b(ikea)\b", "IKEA", "shopping-lifestyle"),
    (r"\b(decathlon)\b", "Decathlon", "shopping-lifestyle"),
    (r"\b(zara|uniqlo|h&m|lifestyle|shoppers\s*stop)\b", "Fashion Apparel", "shopping-lifestyle"),

    # Health & Fitness
    (r"\b(apollo\s*pharmacy)\b", "Apollo Pharmacy", "health-fitness"),
    (r"\b(medplus)\b", "Medplus", "health-fitness"),
    (r"\b(pharmeasy)\b", "PharmEasy", "health-fitness"),
    (r"\b(1mg|tata\s*1mg)\b", "Tata 1mg", "health-fitness"),
    (r"\b(cult\.?fit|cure\.?fit)\b", "Cult.fit", "health-fitness"),
    (r"\b(practo)\b", "Practo", "health-fitness"),
    (r"\b(manipal|max\s*healthcare|fortis)\b", "Hospital Healthcare", "health-fitness"),
    (r"\b(dr\s*lal|metropolis|pathology)\b", "Diagnostic Lab", "health-fitness"),

    # Subscriptions & Entertainment
    (r"\b(netflix)\b", "Netflix", "subscriptions"),
    (r"\b(spotify)\b", "Spotify", "subscriptions"),
    (r"\b(youtube\s*prem|google\s*youtube)\b", "YouTube Premium", "subscriptions"),
    (r"\b(disney|hotstar)\b", "Disney+ Hotstar", "subscriptions"),
    (r"\b(apple\s*services|apple\.com|itunes)\b", "Apple Services", "subscriptions"),
    (r"\b(google\s*one|google\s*storage)\b", "Google One", "subscriptions"),
    (r"\b(github)\b", "GitHub", "subscriptions"),
    (r"\b(openai|chatgpt)\b", "OpenAI", "subscriptions"),
    (r"\b(bookmyshow)\b", "BookMyShow", "entertainment-ott"),
    (r"\b(pvr|inox|cinepolis)\b", "PVR INOX", "entertainment-ott"),

    # Education
    (r"\b(coursera)\b", "Coursera", "education"),
    (r"\b(udemy)\b", "Udemy", "education"),
    (r"\b(upgrad|scaler|interviewbit)\b", "EdTech Platform", "education"),
    (r"\b(allen|aakash|coaching|tuition)\b", "Education Coaching", "education"),

    # Salary & Freelance
    (r"\b(infosys|tcs|wipro|cognizant|accenture|hcl\s*tech|google\s*india|microsoft\s*india)\b.*(salary|payroll)", "Employer Payroll", "salary"),
    (r"\b(salary\s*cr|ach\s*cr.*salary|monthly\s*salary)\b", "Salary Credit", "salary"),
    (r"\b(upwork|toptal|fiverr|freelance|consulting\s*fee)\b", "Freelance Client", "freelance"),

    # Investments
    (r"\b(zerodha)\b", "Zerodha", "investments-sip"),
    (r"\b(groww)\b", "Groww", "investments-sip"),
    (r"\b(kuvera)\b", "Kuvera", "investments-sip"),
    (r"\b(mutual\s*fund|sip\s*investment|ppfas|nippon|mirae|uti\s*mf)\b", "Mutual Fund SIP", "investments-sip"),
    (r"\b(ppf\s*deposit|nps\s*cra|sgb)\b", "Government Schemes", "investments-sip"),

    # Refunds & Cashback
    (r"\b(refund|reversed|cashback|cash\s*back|reward)\b", "Merchant Refund", "refunds-cashback"),

    # Bank Charges
    (r"\b(sms\s*charges|annual\s*maintenance|amc\s*fee|card\s*fee|chq\s*chg|atm\s*chg)\b", "Bank Charges", "fees-charges"),
]

def normalize_merchant(narration: str) -> Optional[str]:
    """Extract and normalize canonical merchant name from raw narration."""
    if not narration:
        return None
    lower = narration.lower()
    for pattern, canonical_name, _ in MERCHANT_PATTERNS:
        if re.search(pattern, lower):
            return canonical_name
    return None

def categorize_transaction(
    narration: str,
    tx_type: str = "DEBIT",
    amount_inr: float = 0.0,
    db_session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Enrich and categorize transaction using:
    1. High-confidence heuristic rules and canonical merchant table
    2. Trained TF-IDF + Logistic Regression ML classifier
    3. Low-confidence flag for manual review
    """
    clean_narration = " ".join(narration.strip().split())
    lower = clean_narration.lower()

    # Special rule: Explicit Refund / Cashback
    if "refund" in lower or "cashback" in lower or "reward" in lower:
        return {
            "category_slug": "refunds-cashback",
            "merchant_name": normalize_merchant(clean_narration) or "Refund/Cashback",
            "method": "RULE",
            "confidence": 0.99,
            "needs_review": False,
        }

    # Special rule: Salary Credit
    if tx_type == "CREDIT" and any(k in lower for k in ["salary", "payroll", "remuneration", "direct dep", "ach cr"]):
        return {
            "category_slug": "salary",
            "merchant_name": normalize_merchant(clean_narration) or "Employer",
            "method": "RULE",
            "confidence": 0.99,
            "needs_review": False,
        }

    # Step 1: Rule-based exact merchant match
    for pattern, canonical_merchant, cat_slug in MERCHANT_PATTERNS:
        if re.search(pattern, lower):
            return {
                "category_slug": cat_slug,
                "merchant_name": canonical_merchant,
                "method": "RULE",
                "confidence": 0.95,
                "needs_review": False,
            }

    # Step 2: Machine Learning Inference Fallback
    try:
        clf = get_transaction_classifier()
        predicted_slug, confidence = clf.predict(clean_narration)
        needs_review = confidence < 0.65

        # Check if merchant normalization yielded anything
        canonical = normalize_merchant(clean_narration)

        return {
            "category_slug": predicted_slug,
            "merchant_name": canonical,
            "method": "ML",
            "confidence": confidence,
            "needs_review": needs_review,
        }
    except Exception:
        # Fallback if ML engine fails or model is loading
        return {
            "category_slug": "miscellaneous",
            "merchant_name": None,
            "method": "RULE",
            "confidence": 0.50,
            "needs_review": True,
        }

def record_user_correction(
    db: Session,
    transaction_id: Union[str, uuid.UUID],
    new_category_id: Union[str, uuid.UUID],
    user_id: Union[str, uuid.UUID],
) -> Transaction:
    """
    Record user feedback when reclassifying a transaction.
    Guarantees user manual corrections are never overwritten by automated jobs.
    """
    if isinstance(transaction_id, str):
        try:
            transaction_id = uuid.UUID(transaction_id)
        except ValueError:
            pass
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            pass
    if isinstance(new_category_id, str):
        try:
            new_category_id = uuid.UUID(new_category_id)
        except ValueError:
            pass

    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise NotFoundException("Transaction", transaction_id)
    if tx.user_id != user_id:
        raise ForbiddenException("You do not have permission to modify this transaction.")

    category = db.query(TransactionCategory).filter(TransactionCategory.id == new_category_id).first()
    if not category:
        raise NotFoundException("TransactionCategory", new_category_id)

    tx.category_id = category.id
    tx.categorization_method = "MANUAL"
    tx.categorization_confidence = 1.0
    db.commit()
    db.refresh(tx)
    return tx
