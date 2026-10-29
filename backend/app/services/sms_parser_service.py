import re
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SMSParseResult(BaseModel):
    success: bool
    bank_name: Optional[str] = None
    account_mask: Optional[str] = None
    account_type: str = "SAVINGS"  # SAVINGS, CREDIT_CARD, WALLET
    transaction_type: str = "DEBIT"  # DEBIT or CREDIT
    amount_inr: float = 0.0
    amount_paise: int = 0
    merchant_name: Optional[str] = None
    raw_narration: str = ""
    clean_narration: str = ""
    suggested_category_slug: Optional[str] = None
    reference_id: Optional[str] = None
    available_balance_inr: Optional[float] = None
    available_balance_paise: Optional[int] = None
    date: str = Field(default_factory=lambda: date.today().isoformat())
    parsing_engine: str = "REGEX_RULES"
    confidence: float = 1.0
    error: Optional[str] = None

class BaseSMSParser:
    """Extension point for bank SMS parsers."""
    def parse(self, text: str) -> SMSParseResult:
        raise NotImplementedError

class RegexBankSMSParser(BaseSMSParser):
    """
    Robust rule-based SMS transaction parser supporting major Indian retail banks
    (HDFC, ICICI, SBI, Axis, Kotak, PayTM, PhonePe, Google Pay).
    """

    def parse(self, text: str) -> SMSParseResult:
        if not text or not text.strip():
            return SMSParseResult(success=False, error="Empty SMS text provided", raw_narration=text or "")

        raw = text.strip()
        lower = raw.lower()

        # 1. Identify Movement Direction (DEBIT vs CREDIT)
        is_credit = False
        is_debit = False

        credit_keywords = ["credited", "deposited", "received", "refunded", "added to", "cr to"]
        debit_keywords = ["debited", "spent", "paid", "withdrawn", "dr from", "deducted", "purchase at"]

        for kw in credit_keywords:
            if kw in lower:
                is_credit = True
                break

        for kw in debit_keywords:
            if kw in lower:
                is_debit = True
                break

        # Disambiguate if both appear (e.g., "refund credited after debit")
        if is_credit and is_debit:
            if "refund" in lower or "cashback" in lower or "credited" in lower:
                is_credit = True
                is_debit = False
            else:
                is_debit = True
                is_credit = False
        elif not is_credit and not is_debit:
            # Default fallback check
            if "cr" in lower and "dr" not in lower:
                is_credit = True
            else:
                is_debit = True

        tx_type = "CREDIT" if is_credit else "DEBIT"

        # 2. Extract Amount
        # Handles: INR 1,250.00, Rs. 450, Rs 12,000.50, INR150, Rs.100.00
        amount_patterns = [
            r"(?:inr|rs\.?|inr\.)\s*([\d,]+\.?\d*)",
            r"(?:for|of|amount)\s*(?:inr|rs\.?)\s*([\d,]+\.?\d*)",
            r"(?:paid|spent|debited|credited)\s*([\d,]+\.?\d*)",
        ]

        amount_inr = 0.0
        for pat in amount_patterns:
            match = re.search(pat, raw, re.IGNORECASE)
            if match:
                raw_amt = match.group(1).replace(",", "")
                try:
                    val = float(raw_amt)
                    if val > 0:
                        amount_inr = val
                        break
                except ValueError:
                    continue

        if amount_inr <= 0:
            return SMSParseResult(
                success=False,
                error="Could not extract valid monetary transaction amount from SMS",
                raw_narration=raw,
            )

        amount_paise = int(round(amount_inr * 100))

        # 3. Extract Bank Name & Account / Card Suffix
        bank_name = None
        for b in ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "INDUSIND", "PUNJAB NATIONAL", "BANK OF BARODA", "PAYTM", "PHONEPE", "GOOGLE PAY"]:
            if re.search(r"\b" + re.escape(b) + r"\b", raw, re.IGNORECASE):
                bank_name = b.upper()
                break

        account_mask = None
        account_type = "SAVINGS"

        # Detect Card vs Account
        if "card" in lower or "credit card" in lower:
            account_type = "CREDIT_CARD"
            card_match = re.search(r"card(?:\s*(?:ending|no|\.))?\s*([xX\*]*\d{4})", raw, re.IGNORECASE)
            if card_match:
                account_mask = re.sub(r"[^\d]", "", card_match.group(1))[-4:]
        else:
            acct_match = re.search(r"(?:a/c|acct|account)(?:\s*(?:ending|no|\.))?\s*([xX\*]*\d{4})", raw, re.IGNORECASE)
            if acct_match:
                account_mask = re.sub(r"[^\d]", "", acct_match.group(1))[-4:]

        # 4. Extract Merchant / Counterparty
        # First check canonical normalizer across the whole text
        from app.services.categorization_service import normalize_merchant
        merchant = normalize_merchant(raw)

        if not merchant:
            merchant_patterns = [
                r"(?:at|to|towards|vpa|info:?\s*upi-?)\s+([A-Za-z0-9\.\*\s&'-]+?)(?=[,\.]?\s+(?:on|ref|avail|bal|using|info)|[,\.]?$)",
                r"(?:by|from)\s+([A-Za-z0-9\.\*\s&'-]+?)(?=[,\.]?\s+(?:on|ref|avail|bal|using|info)|[,\.]?$)",
            ]
            for mp in merchant_patterns:
                mm = re.search(mp, raw, re.IGNORECASE)
                if mm:
                    cand = mm.group(1).strip().strip(".,")
                    cand = re.sub(r"\b(upi|inr|rs|bank|your|account|card)\b", "", cand, flags=re.IGNORECASE).strip()
                    if cand and len(cand) > 1 and not cand.isdigit():
                        merchant = cand.title()
                        break

        # 5. Extract Reference ID (UPI Ref, UTR, Txn ID, UPI/...)
        ref_id = None
        ref_match = re.search(r"(?:upi(?:\s*ref(?:erence)?)?[\s/:]+|utr(?:\s*no\.?)?[\s/:]+|ref\s*no\.?[\s/:]+|txn\s*id[\s/:]+)([A-Za-z0-9]{6,})", raw, re.IGNORECASE)
        if ref_match:
            ref_id = ref_match.group(1)

        # 6. Extract Available Balance when present
        avail_bal_inr = None
        avail_bal_paise = None
        bal_match = re.search(r"(?:avail(?:able)?\s*(?:bal(?:ance)?|limit)?|bal(?:ance)?)\s*:?\s*(?:inr|rs\.?)?\s*([\d,]+\.?\d*)", raw, re.IGNORECASE)
        if bal_match:
            try:
                b_val = float(bal_match.group(1).replace(",", ""))
                avail_bal_inr = b_val
                avail_bal_paise = int(round(b_val * 100))
            except ValueError:
                pass

        # 7. Extract Date when present
        tx_date_str = date.today().isoformat()
        date_match = re.search(r"\b(\d{1,2}[-/](?:[a-zA-Z]{3}|\d{1,2})[-/]\d{2,4})\b", raw)
        if date_match:
            raw_d = date_match.group(1)
            for fmt in ["%d-%b-%y", "%d-%b-%Y", "%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y"]:
                try:
                    dt = datetime.strptime(raw_d, fmt)
                    # Adjust century if 2-digit year was parsed into 1900s
                    if dt.year < 2000:
                        dt = dt.replace(year=dt.year + 100)
                    tx_date_str = dt.date().isoformat()
                    break
                except ValueError:
                    continue

        clean_narration = f"{merchant or 'Payment'} via SMS Parser" if tx_type == "DEBIT" else f"Credit from {merchant or 'Unknown'}"

        return SMSParseResult(
            success=True,
            bank_name=bank_name,
            account_mask=account_mask,
            account_type=account_type,
            transaction_type=tx_type,
            amount_inr=amount_inr,
            amount_paise=amount_paise,
            merchant_name=merchant,
            raw_narration=raw,
            clean_narration=clean_narration,
            reference_id=ref_id,
            available_balance_inr=avail_bal_inr,
            available_balance_paise=avail_bal_paise,
            date=tx_date_str,
            parsing_engine="REGEX_RULES",
            confidence=0.96,
        )

# Factory / Plugin extension point
_sms_parser_instance: Optional[BaseSMSParser] = None

def get_sms_parser() -> BaseSMSParser:
    global _sms_parser_instance
    if _sms_parser_instance is None:
        _sms_parser_instance = RegexBankSMSParser()
    return _sms_parser_instance
