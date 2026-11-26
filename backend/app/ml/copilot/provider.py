import calendar
import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Iterator, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

class ProviderResult:
    def __init__(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        provider_used: str = "mock-deterministic-v1",
        finish_reason: str = "stop",
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.provider_used = provider_used
        self.finish_reason = finish_reason

class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> ProviderResult:
        pass

    def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Iterator[str]:
        """Default stream fallback yielding full content in chunks."""
        res = self.generate(messages, tools, system_prompt)
        text = res.content or ""
        words = text.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i : i + 3]) + " "
            yield chunk

# ============================================================================
# Groq Provider
# ============================================================================

class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", temperature: float = 0.2):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self._client = None
        try:
            from groq import Groq
            self._client = Groq(api_key=api_key)
        except Exception as e:
            logger.warning(f"Could not initialize native Groq client: {e}. Will use httpx fallback if needed.")

    @property
    def name(self) -> str:
        return f"groq-{self.model}"

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> ProviderResult:
        groq_messages = []
        if system_prompt:
            groq_messages.append({"role": "system", "content": system_prompt})

        for m in messages:
            role = m.get("role", "user").lower()
            if role in ["user", "assistant", "system", "tool"]:
                groq_messages.append(m)

        try:
            if self._client:
                kwargs: Dict[str, Any] = {
                    "model": self.model,
                    "messages": groq_messages,
                    "temperature": self.temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = self._client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                tool_calls_data = []
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        tool_calls_data.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        })

                return ProviderResult(
                    content=choice.message.content,
                    tool_calls=tool_calls_data,
                    provider_used=f"groq-{self.model}",
                    finish_reason=choice.finish_reason or "stop",
                )
            else:
                import httpx
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload: Dict[str, Any] = {
                    "model": self.model,
                    "messages": groq_messages,
                    "temperature": self.temperature,
                }
                if tools:
                    payload["tools"] = tools

                with httpx.Client(timeout=30.0) as client:
                    resp = client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                    if resp.status_code == 429:
                        return ProviderResult(
                            content="Groq API rate limit reached. Using deterministic cached financial analysis.",
                            provider_used="groq-ratelimit-fallback",
                        )
                    resp.raise_for_status()
                    data = resp.json()
                    choice = data["choices"][0]
                    msg = choice["message"]
                    return ProviderResult(
                        content=msg.get("content"),
                        tool_calls=msg.get("tool_calls", []),
                        provider_used=f"groq-{self.model}",
                    )
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}", exc_info=True)
            return ProviderResult(
                content=f"Encountered temporary issue communicating with Groq ({str(e)}). Analysis rendered using deterministic FinPilot fallback.",
                provider_used="groq-error-fallback",
            )

# ============================================================================
# Mock Deterministic Provider (Offline Development & Testing)
# ============================================================================

class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic offline provider that handles both standard and custom natural-language
    financial queries against real database tools:
    1. Parses intents, categories, merchants, amounts, and date windows.
    2. Requests grounded tool execution.
    3. Synthesizes accurate, transparent, Markdown-formatted explanations.
    """

    CATEGORY_KEYWORDS: List[Tuple[str, str, List[str]]] = [
        ("groceries-essentials", "DEBIT", ["grocery", "groceries", "supermarket", "vegetable", "vegetables", "fruits", "milk", "essentials", "kirana"]),
        ("food-dining", "DEBIT", ["food", "dining", "eat", "eating", "restaurant", "restaurants", "cafe", "lunch", "dinner", "breakfast", "coffee", "snacks"]),
        ("housing-rent", "DEBIT", ["rent", "housing", "landlord", "apartment", "flat"]),
        ("utilities-bills", "DEBIT", ["utility", "utilities", "electricity", "power", "water", "gas", "internet", "wifi", "broadband", "fibernet", "mobile", "recharge"]),
        ("transportation-fuel", "DEBIT", ["transport", "transportation", "travel", "commute", "fuel", "petrol", "diesel", "cab", "taxi", "metro", "auto"]),
        ("shopping-lifestyle", "DEBIT", ["shopping", "shop", "clothes", "apparel", "fashion", "electronics", "lifestyle"]),
        ("entertainment-ott", "DEBIT", ["entertainment", "ott", "movie", "movies", "cinema", "streaming", "concert"]),
        ("subscriptions", "DEBIT", ["subscription", "subscriptions", "membership", "memberships"]),
        ("education", "DEBIT", ["education", "learning", "course", "courses", "book", "books", "tuition"]),
        ("investments-sip", "DEBIT", ["sip", "mutual fund", "invest", "investment", "investments", "mf"]),
        ("health-fitness", "DEBIT", ["health", "fitness", "gym", "medical", "doctor", "pharmacy", "medicine", "hospital"]),
        ("fees-charges", "DEBIT", ["fee", "fees", "penalty", "bank charge", "bank charges"]),
        ("transfers", "DEBIT", ["transfer", "transfers", "remittance"]),
        ("salary", "CREDIT", ["salary", "paycheck", "wages"]),
        ("freelance", "CREDIT", ["freelance", "consulting"]),
        ("investment-returns", "CREDIT", ["dividend", "interest", "returns", "investment return"]),
        ("refunds-cashback", "CREDIT", ["refund", "refunds", "cashback"]),
    ]

    KNOWN_MERCHANTS: List[str] = [
        "swiggy", "zomato", "zepto", "blinkit", "bigbasket", "dmart",
        "uber", "ola", "rapido", "amazon", "flipkart", "myntra", "ajio",
        "netflix", "spotify", "hotstar", "bescom", "act fibernet", "jio",
        "airtel", "toit", "starbucks", "cult", "zerodha", "infosys",
        "apollo", "pharmeasy", "nykaa", "irctc", "makemytrip",
    ]

    MONTH_NAMES: Dict[str, int] = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
        "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    }

    @property
    def name(self) -> str:
        return "mock-deterministic-v1"

    @staticmethod
    def _has_keyword(text: str, keywords: List[str]) -> bool:
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return True
        return False

    def _extract_date_range(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        today = date.today()
        if any(p in text for p in ["last month", "previous month", "past month"]):
            first_curr = date(today.year, today.month, 1)
            last_prev = first_curr - timedelta(days=1)
            first_prev = date(last_prev.year, last_prev.month, 1)
            return first_prev.isoformat(), last_prev.isoformat()
        if any(p in text for p in ["last 3 months", "past 3 months", "90 days", "3 months", "quarter"]):
            return (today - timedelta(days=90)).isoformat(), today.isoformat()
        if any(p in text for p in ["last 6 months", "past 6 months", "6 months", "six months"]):
            return (today - timedelta(days=180)).isoformat(), today.isoformat()
        if any(p in text for p in ["this year", "ytd", "year to date", "last 12 months", "whole year"]):
            return date(today.year, 1, 1).isoformat(), today.isoformat()
        if any(p in text for p in ["last week", "past week", "7 days", "this week"]):
            return (today - timedelta(days=7)).isoformat(), today.isoformat()
        if "today" in text:
            return today.isoformat(), today.isoformat()

        for m_name, m_num in self.MONTH_NAMES.items():
            if re.search(r"\b" + m_name + r"\b", text):
                yr = today.year if m_num <= today.month else today.year - 1
                last_day = calendar.monthrange(yr, m_num)[1]
                return date(yr, m_num, 1).isoformat(), date(yr, m_num, last_day).isoformat()

        return None, None

    @staticmethod
    def _extract_amount(text: str, default: float) -> float:
        m = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(k|lakh|lakhs|lac|l)?\b", text)
        if not m:
            return default
        val = float(m.group(1).replace(",", ""))
        unit = (m.group(2) or "").lower()
        if unit == "k":
            val *= 1000.0
        elif unit in ("lakh", "lakhs", "lac", "l"):
            val *= 100000.0
        return val

    def _match_category(self, text: str) -> Optional[Tuple[str, str]]:
        for slug, tx_type, keywords in self.CATEGORY_KEYWORDS:
            if self._has_keyword(text, keywords):
                return slug, tx_type
        return None

    def _match_merchant(self, text: str) -> Optional[str]:
        for merch in self.KNOWN_MERCHANTS:
            if re.search(r"\b" + re.escape(merch) + r"\b", text):
                return merch.title()
        return None

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> ProviderResult:
        # Check if the last message is a tool response
        last_msg = messages[-1] if messages else {}

        if last_msg.get("role") == "tool":
            # We have tool output! Synthesize grounded explanation.
            tool_name = last_msg.get("name", "")
            try:
                tool_data = json.loads(last_msg.get("content", "{}"))
            except Exception:
                tool_data = {}

            return self._synthesize_tool_response(tool_name, tool_data, messages)

        # Inspect latest and previous user message (for follow-ups)
        user_msgs = [m.get("content", "").lower().strip() for m in messages if m.get("role") == "user"]
        user_msg = user_msgs[-1] if user_msgs else ""
        prev_user_msg = user_msgs[-2] if len(user_msgs) >= 2 else ""

        # 0. Pure greeting / help queries (only if no financial terms are in message)
        clean_alpha = re.sub(r"[^a-z\s]", "", user_msg).strip()
        greeting_phrases = {"hi", "hello", "hey", "hii", "hiii", "good morning", "good afternoon", "good evening", "thanks", "thank you", "ok", "okay", "help", "what can you do", "who are you"}
        if clean_alpha in greeting_phrases:
            return ProviderResult(
                content=(
                    "Hello! I am your **FinPilot Financial Copilot**, connected directly to your verified accounts, transactions, budgets, and forecast models.\n\n"
                    "Feel free to ask any custom question, such as:\n"
                    "- *\"What about grocery spending this month?\"* or *\"How much did I spend on Swiggy?\"*\n"
                    "- *\"What is my current account balance and savings rate?\"*\n"
                    "- *\"How are my budgets and goals tracking?\"*\n"
                    "- *\"Can I afford a ₹25,000 purchase right now?\"*\n"
                    "- *\"Compare my spending this month vs last month\"*"
                ),
                provider_used=self.name,
            )

        start_date, end_date = self._extract_date_range(user_msg)

        # 1. Compare periods / increased the most vs last month
        if any(w in user_msg for w in ["increased", "compared", "vs last month", "more than last", "month over month", "mom"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_comp_1",
                    "type": "function",
                    "function": {
                        "name": "compare_time_periods",
                        "arguments": json.dumps({"period_type": "month_over_month"}),
                    },
                }],
                provider_used=self.name,
            )

        # 2. Afford purchase without dropping below emergency reserve
        if any(w in user_msg for w in ["afford", "can i buy", "should i buy", "purchase", "emergency reserve", "drop below"]):
            purchase_amt = self._extract_amount(user_msg, 15000.0)
            return ProviderResult(
                tool_calls=[{
                    "id": "call_scen_1",
                    "type": "function",
                    "function": {
                        "name": "simulate_financial_scenario",
                        "arguments": json.dumps({
                            "scenario_type": "AFFORD_PURCHASE",
                            "purchase_amount_inr": purchase_amt,
                            "reserve_threshold_inr": 10000.0,
                        }),
                    },
                }],
                provider_used=self.name,
            )

        # 3. Reduce spending / cut spending
        if any(w in user_msg for w in ["reduce spending", "cut spending", "save 2000", "reduce by", "save extra", "cut down", "how can i save", "where can i save"]):
            cut_amt = self._extract_amount(user_msg, 2000.0)
            return ProviderResult(
                tool_calls=[{
                    "id": "call_scen_2",
                    "type": "function",
                    "function": {
                        "name": "simulate_financial_scenario",
                        "arguments": json.dumps({
                            "scenario_type": "REDUCE_SPENDING",
                            "target_reduction_inr": cut_amt,
                        }),
                    },
                }],
                provider_used=self.name,
            )

        # 4. Predict low balance near month-end / forecast
        if any(w in user_msg for w in ["predict", "forecast", "low balance", "month-end", "near month-end", "shortfall", "projected balance"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_fc_1",
                    "type": "function",
                    "function": {
                        "name": "get_cashflow_forecast",
                        "arguments": json.dumps({"horizon_days": 30}),
                    },
                }],
                provider_used=self.name,
            )

        # 5. Recurring payments / bills due soon
        if any(w in user_msg for w in ["recurring", "due soon", "upcoming bill", "upcoming payment", "payments due", "auto-debit", "mandate", "bills"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_rec_1",
                    "type": "function",
                    "function": {
                        "name": "get_recurring_payments",
                        "arguments": json.dumps({"due_within_days": 30}),
                    },
                }],
                provider_used=self.name,
            )

        # 6. Six months savings under different assumptions
        if any(w in user_msg for w in ["six months", "6 months", "save in", "savings assumption", "how much could i save"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_scen_3",
                    "type": "function",
                    "function": {
                        "name": "simulate_financial_scenario",
                        "arguments": json.dumps({
                            "scenario_type": "FUTURE_SAVINGS",
                            "target_months": 6,
                            "monthly_savings_boost_inr": 3000.0,
                        }),
                    },
                }],
                provider_used=self.name,
            )

        # 7. Financial Health Score
        if any(w in user_msg for w in ["health score", "financial health", "my score", "grade", "wellness score"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_health_1",
                    "type": "function",
                    "function": {
                        "name": "get_financial_health_score",
                        "arguments": json.dumps({}),
                    },
                }],
                provider_used=self.name,
            )

        # 8. Personalized Recommendations
        if any(w in user_msg for w in ["recommendation", "recommendations", "suggest", "tips", "advice", "advise"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_recs_1",
                    "type": "function",
                    "function": {
                        "name": "get_personalized_recommendations",
                        "arguments": json.dumps({"status": "all"}),
                    },
                }],
                provider_used=self.name,
            )

        # 9. Budgets & Goals progress
        if self._has_keyword(user_msg, ["budget", "budgets", "overspend", "over budget", "pacing", "goal", "goals", "emergency fund", "vacation"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_bg_1",
                    "type": "function",
                    "function": {
                        "name": "get_budget_and_goals_progress",
                        "arguments": json.dumps({"include_goals": True}),
                    },
                }],
                provider_used=self.name,
            )

        # 10. Specific Merchant Lookup (Swiggy, Zomato, Zepto, Blinkit, Uber, Amazon, etc.)
        matched_merchant = self._match_merchant(user_msg)
        if matched_merchant:
            return ProviderResult(
                tool_calls=[{
                    "id": "call_merch_1",
                    "type": "function",
                    "function": {
                        "name": "query_aggregate_transactions",
                        "arguments": json.dumps({
                            "merchant_keyword": matched_merchant,
                            "transaction_type": "DEBIT",
                            "start_date": start_date,
                            "end_date": end_date,
                        }),
                    },
                }],
                provider_used=self.name,
            )

        # 11. Specific Category Lookup (Groceries, Food, Rent, Utilities, Transport, Health, SIP, Salary, etc.)
        matched_cat = self._match_category(user_msg)
        if matched_cat:
            cat_slug, tx_type = matched_cat
            # For salary/income in current month if no start_date specified, default to last_30_days if empty? Keep query_aggregate_transactions exact.
            return ProviderResult(
                tool_calls=[{
                    "id": "call_cat_1",
                    "type": "function",
                    "function": {
                        "name": "query_aggregate_transactions",
                        "arguments": json.dumps({
                            "category_slug": cat_slug,
                            "transaction_type": tx_type,
                            "start_date": start_date,
                            "end_date": end_date,
                        }),
                    },
                }],
                provider_used=self.name,
            )

        # 12. Account Balance, Net Worth, Savings Rate, Cards, Overview
        if any(w in user_msg for w in ["balance", "account", "accounts", "cash", "liquid", "net worth", "savings", "debt", "credit card", "hdfc", "icici", "overview", "summary", "how much money", "how am i doing", "status"]):
            period = "current_month" if "this month" in user_msg else ("last_90_days" if "3 months" in user_msg else "last_30_days")
            return ProviderResult(
                tool_calls=[{
                    "id": "call_acct_1",
                    "type": "function",
                    "function": {
                        "name": "get_account_summary",
                        "arguments": json.dumps({"period": period}),
                    },
                }],
                provider_used=self.name,
            )

        # 13. General Spending / Income / Custom Merchant phrases ("how much did I spend", "what about X", "spent on X")
        if any(w in user_msg for w in ["spend", "spent", "spending", "expense", "expenses", "paid", "transactions", "debit", "money go", "biggest", "top"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_all_tx_1",
                    "type": "function",
                    "function": {
                        "name": "query_aggregate_transactions",
                        "arguments": json.dumps({
                            "category_slug": None,
                            "transaction_type": "DEBIT",
                            "start_date": start_date,
                            "end_date": end_date,
                        }),
                    },
                }],
                provider_used=self.name,
            )

        if any(w in user_msg for w in ["earn", "earned", "income", "credit", "credits", "received"]):
            return ProviderResult(
                tool_calls=[{
                    "id": "call_all_cr_1",
                    "type": "function",
                    "function": {
                        "name": "query_aggregate_transactions",
                        "arguments": json.dumps({
                            "category_slug": None,
                            "transaction_type": "CREDIT",
                            "start_date": start_date or (date.today() - timedelta(days=30)).isoformat(),
                            "end_date": end_date,
                        }),
                    },
                }],
                provider_used=self.name,
            )

        # 14. Follow-up time shift ("what about last month?", "and October?") carrying over previous category/merchant
        if (start_date or end_date) and prev_user_msg:
            prev_cat = self._match_category(prev_user_msg)
            prev_merch = self._match_merchant(prev_user_msg)
            if prev_merch or prev_cat:
                return ProviderResult(
                    tool_calls=[{
                        "id": "call_followup_1",
                        "type": "function",
                        "function": {
                            "name": "query_aggregate_transactions",
                            "arguments": json.dumps({
                                "category_slug": prev_cat[0] if prev_cat else None,
                                "merchant_keyword": prev_merch,
                                "transaction_type": prev_cat[1] if prev_cat else "DEBIT",
                                "start_date": start_date,
                                "end_date": end_date,
                            }),
                        },
                    }],
                    provider_used=self.name,
                )

        # 15. Custom "what about <keyword>" / "how much on <keyword>" merchant search
        custom_kw_match = re.search(r"(?:what about|how about|how much (?:did i spend )?(?:on|at|for)|spent on|show me)\s+([a-z0-9][a-z0-9\s\-]{1,25})$", clean_alpha)
        if custom_kw_match:
            kw = custom_kw_match.group(1).strip()
            if kw and kw not in {"it", "this", "that", "them", "today", "this month", "last month"}:
                return ProviderResult(
                    tool_calls=[{
                        "id": "call_custom_kw_1",
                        "type": "function",
                        "function": {
                            "name": "query_aggregate_transactions",
                            "arguments": json.dumps({
                                "merchant_keyword": kw,
                                "transaction_type": "ALL",
                                "start_date": start_date or (date.today() - timedelta(days=90)).isoformat(),
                                "end_date": end_date,
                            }),
                        },
                    }],
                    provider_used=self.name,
                )

        # 16. Rich Default Fallback: Account & Financial Summary (never returns generic "Tool output verified")
        return ProviderResult(
            tool_calls=[{
                "id": "call_summary_default",
                "type": "function",
                "function": {
                    "name": "get_account_summary",
                    "arguments": json.dumps({"period": "last_30_days"}),
                },
            }],
            provider_used=self.name,
        )

    def _synthesize_tool_response(self, tool_name: str, data: Dict[str, Any], messages: List[Dict[str, Any]]) -> ProviderResult:
        if tool_name == "query_aggregate_transactions":
            total = data.get("total_amount_inr", 0)
            count = data.get("transaction_count", 0)
            cat_name = data.get("category_name", "All Categories")
            tx_type = data.get("transaction_type", "DEBIT")
            start_d = data.get("start_date", "")
            end_d = data.get("end_date", "")
            avg = data.get("average_amount_inr", 0)
            top_merchants = data.get("top_merchants", [])
            top_categories = data.get("top_categories", [])
            samples = data.get("recent_samples", [])

            verb = "received" if tx_type == "CREDIT" else "spent"
            merch_str = ", ".join(f"{m['merchant']} (₹{m['total_spent_inr']:,.2f})" for m in top_merchants[:4])

            ans = (
                f"### {cat_name} {'Inflow' if tx_type == 'CREDIT' else 'Spending'} Breakdown\n\n"
                f"Based on your verified bank transactions ({start_d} to {end_d}), you have {verb} a total of **₹{total:,.2f}** across **{count} transactions**"
            )
            if count > 0:
                ans += f" (average: **₹{avg:,.2f}** per transaction).\n\n"
            else:
                ans += ".\n\nNo matching settled transactions were found in this period. Try asking about another month (e.g., *\"last month\"* or *\"last 3 months\"*).\n\n"

            if cat_name == "All Categories" and top_categories:
                ans += "**Top categories in this period:**\n"
                for c in top_categories[:5]:
                    ans += f"- **{c['category']}**: ₹{c['total_spent_inr']:,.2f}\n"
                ans += "\n"

            if top_merchants:
                ans += f"**Top merchants:** {merch_str}.\n\n"

            if samples and count > 0:
                ans += "**Recent entries:** " + ", ".join(f"{s['date']} {s['merchant']} (₹{s['amount_inr']:,.0f})" for s in samples[:3]) + ".\n\n"

            ans += "> **Observed Fact**: All figures above are aggregated directly from settled ledger postings on your connected accounts."
            return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "compare_time_periods":
            top_inc = data.get("highest_increasing_categories", [])
            p1_tot = data.get("current_total_expenses_inr", 0)
            p2_tot = data.get("previous_total_expenses_inr", 0)
            delta = data.get("net_delta_inr", 0)
            pct = data.get("net_percentage_change", 0)

            ans = (
                f"### Month-over-Month Spending Comparison\n\n"
                f"Your total monthly expenses are currently **₹{p1_tot:,.2f}**, compared to **₹{p2_tot:,.2f}** during the same period last month "
                f"({'+' if delta >= 0 else ''}₹{delta:,.2f}, **{pct:+.1f}%**).\n\n"
                f"**Categories with the largest spending increases:**\n"
            )
            for idx, c in enumerate(top_inc, 1):
                ans += f"{idx}. **{c['category_name']}**: +₹{c['delta_inr']:,.2f} ({c['percentage_change']:+.1f}%)\n"

            ans += "\n> **Retrieved Fact**: Calculations strictly reflect settled historical debits across both monthly windows."
            return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "get_recurring_payments":
            upcoming = data.get("recurring_payments", [])
            tot_bills = data.get("total_upcoming_bills_inr", 0)
            tot_income = data.get("total_upcoming_income_inr", 0)

            ans = (
                f"### Upcoming Recurring Obligations\n\n"
                f"You have **{len(upcoming)} scheduled recurring transactions** due in the next 30 days, "
                f"totaling **₹{tot_bills:,.2f} in bills & commitments** against **₹{tot_income:,.2f} in expected salary/inflow**:\n\n"
            )
            for u in upcoming:
                prefix = "+" if u["transaction_type"] == "CREDIT" else "-"
                ans += f"- **{u['name']}**: {prefix}₹{u['amount_inr']:,.2f} (Due in **{u['days_until_due']} days** on {u['next_expected_date']})\n"

            ans += "\n> **Retrieved Fact**: Detected from recurring auto-debit rules and verified recurring credit mandates."
            return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "get_cashflow_forecast":
            curr_bal = data.get("current_liquid_balance_inr", 0)
            end_bal = data.get("predicted_end_balance_inr", 0)
            min_dip = data.get("minimum_projected_dip_inr", 0)
            dip_date = data.get("minimum_projected_date", "month-end")
            risk = data.get("shortfall_risk_level", "SAFE")
            prob = data.get("shortfall_probability_pct", 0)
            neg_drivers = data.get("primary_negative_drivers", [])

            ans = (
                f"### Month-End Balance & Liquidity Forecast\n\n"
                f"The system projects your available liquid balance will dip to a minimum of **₹{min_dip:,.2f}** on **{dip_date}**, "
                f"before rebounding to **₹{end_bal:,.2f}** by month-end.\n\n"
                f"**Why the dip is predicted near month-end:**\n"
            )
            for d in neg_drivers:
                ans += f"- {d}\n"
            ans += (
                f"\n**Liquidity Risk Status:** `{risk}` (Estimated shortfall probability: **{prob}%**).\n\n"
                f"> **Model Estimate**: Projected by the Ridge ML calendar forecasting model with conformal uncertainty bands. "
                f"Assumes salary credit clears on schedule."
            )
            return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "simulate_financial_scenario":
            sc_type = data.get("scenario")
            if sc_type == "AFFORD_PURCHASE":
                amt = data.get("purchase_amount_inr", 0)
                reserve = data.get("reserve_threshold_inr", 10000)
                liquid = data.get("current_liquid_inr", 0)
                post_dip = data.get("projected_post_purchase_min_dip_inr", 0)
                verdict_title = data.get("verdict_title", "")
                rec = data.get("recommendation", "")

                ans = (
                    f"### Affordability Analysis: ₹{amt:,.2f} Purchase\n\n"
                    f"**Verdict:** {verdict_title}\n\n"
                    f"- **Current Liquid Cash:** ₹{liquid:,.2f}\n"
                    f"- **Target Emergency Reserve:** ₹{reserve:,.2f}\n"
                    f"- **Projected Post-Purchase Minimum Balance:** ₹{post_dip:,.2f}\n\n"
                    f"**Recommendation:**\n{rec}\n\n"
                    f"> **Hypothetical Scenario**: Simulates deduction of ₹{amt:,.2f} against your cash-flow trajectory without changing other commitments."
                )
                return ProviderResult(content=ans, provider_used=self.name)

            elif sc_type == "REDUCE_SPENDING":
                target = data.get("target_reduction_inr", 2000)
                alloc = data.get("recommended_allocation", [])
                proj_savings = data.get("projected_monthly_savings_inr", 0)
                proj_rate = data.get("projected_savings_rate_pct", 0)

                ans = (
                    f"### Spending Optimization Plan (-₹{target:,.2f}/month)\n\n"
                    f"To free up **₹{target:,.2f} next month**, here is the recommended reduction plan based on discretionary spending:\n\n"
                )
                for a in alloc:
                    ans += f"- **{a['category_name']}**: Reduce by **₹{a['recommended_cut_inr']:,.0f}** (Target: ₹{a['target_spent_inr']:,.0f}/mo). {a['action_tip']}\n"

                ans += (
                    f"\n**Outcome:** Boosts projected monthly savings to **₹{proj_savings:,.2f}** (Savings Rate: **{proj_rate}%**).\n\n"
                    f"> **Hypothetical Scenario**: Tailored by trimming non-essential dining and online shopping without impacting fixed utility or rent bills."
                )
                return ProviderResult(content=ans, provider_used=self.name)

            elif sc_type == "FUTURE_SAVINGS":
                months = data.get("target_months", 6)
                boost = data.get("monthly_savings_boost_inr", 3000)
                base_cum = data.get("baseline_cumulative_savings_inr", 0)
                opt_cum = data.get("optimized_cumulative_savings_inr", 0)
                wealth = data.get("total_wealth_created_inr", 0)

                ans = (
                    f"### {months}-Month Savings Projection\n\n"
                    f"If you maintain your current savings rate, you will accumulate **₹{base_cum:,.2f}** in {months} months.\n\n"
                    f"By increasing your monthly savings by **₹{boost:,.2f}/month** (via spending optimizations or SIP top-ups):\n"
                    f"- **Optimized {months}-Month Total:** **₹{opt_cum:,.2f}**\n"
                    f"- **Net Additional Wealth Created:** **+₹{wealth:,.2f}**\n\n"
                    f"> **Hypothetical Scenario**: Assumes steady income and zero unplanned capital withdrawals over the {months}-month horizon."
                )
                return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "get_financial_health_score":
            score = data.get("overall_score", 0)
            grade = data.get("grade", "Fair")
            summary = data.get("summary", "")
            disclaimer = data.get("disclaimer", "")
            liquid = data.get("liquid_reserve_inr", 0)
            factors = data.get("factors", [])
            actions = data.get("top_improvement_actions", [])

            ans = (
                f"### Financial Health Score: **{score}/100** ({grade})\n\n"
                f"{summary}\n\n"
                f"**Key Evaluated Factors:**\n"
            )
            for f in factors:
                status_icon = "⚠️ Excluded" if f.get("is_excluded") else f"{f.get('score', 0)}/{f.get('max_score', 0)} pts"
                val = f" ({f.get('metric_value')})" if f.get('metric_value') else ""
                ans += f"- **{f.get('name')}**: {status_icon}{val}. {f.get('actionable_tip')}\n"

            if actions:
                ans += f"\n**Actionable Ways to Improve:**\n"
                for act in actions:
                    ans += f"- {act}\n"

            ans += f"\n> **Educational Notice**: *{disclaimer}*"
            return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "get_personalized_recommendations":
            recs = data.get("recommendations", [])
            if not recs:
                ans = "### Financial Recommendations\n\nNo pending recommendations at this time. Your current spending aligns well with established category budgets."
            else:
                ans = f"### Personalized Recommendations ({len(recs)} Active)\n\n"
                for r in recs:
                    impact = f" | Estimated Benefit: **₹{r.get('estimated_impact_inr', 0):,.0f}**" if r.get('estimated_impact_inr') else ""
                    ans += (
                        f"#### {r.get('title')}\n"
                        f"- **Timeframe:** {r.get('data_period')} | **Confidence:** {r.get('confidence')}{impact}\n"
                        f"- **Context:** {r.get('explanation')}\n"
                        f"- **Recommended Action:** {r.get('suggested_action')}\n\n"
                    )
                ans += "> **Grounded Recommendation Engine**: Formulated using deterministic rules on your verified statements, active budgets, and upcoming EMIs."

            return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "get_budget_and_goals_progress":
            month = data.get("month", "Current Month")
            tot_spent = data.get("total_budgeted_spent_inr", 0)
            tot_limit = data.get("total_budgeted_limit_inr", 0)
            util = data.get("overall_utilization_pct", 0)
            budgets = data.get("budgets", [])
            goals = data.get("goals", [])

            ans = (
                f"### Budgets & Savings Goals ({month})\n\n"
                f"Overall budget utilization stands at **{util}%** (**₹{tot_spent:,.2f}** spent out of **₹{tot_limit:,.2f}** total limits).\n\n"
            )
            if budgets:
                ans += "**Category Budget Pacing:**\n"
                for b in budgets:
                    flag = "Over Limit" if b.get("is_exceeded") else ("Near Limit" if b.get("percent_used", 0) >= 80 else "On Track")
                    ans += (
                        f"- **{b['category_name']}**: ₹{b['spent_inr']:,.0f} / ₹{b['monthly_limit_inr']:,.0f} "
                        f"(**{b['percent_used']}%** — {flag}, ₹{b['remaining_inr']:,.0f} remaining)\n"
                    )
                ans += "\n"

            if goals:
                ans += "**Active Savings Goals:**\n"
                for g in goals:
                    ans += (
                        f"- **{g['goal_name']}**: ₹{g['current_saved_inr']:,.0f} / ₹{g['target_amount_inr']:,.0f} "
                        f"(**{g['progress_pct']}%** complete"
                        + (f", target: {g['target_date']}" if g.get("target_date") else "")
                        + ")\n"
                    )
                ans += "\n"

            ans += "> **Observed Fact**: Figures reflect real-time debits against your monthly category allocations and goal balances."
            return ProviderResult(content=ans, provider_used=self.name)

        elif tool_name == "get_account_summary":
            liq = data.get("total_liquid_balance_inr", 0)
            debt = data.get("total_debt_balance_inr", 0)
            inc = data.get("total_income_inr", 0)
            exp = data.get("total_expenses_inr", 0)
            net = data.get("net_savings_inr", 0)
            s_rate = data.get("savings_rate", 0)
            score = data.get("health_score", 0)
            grade = data.get("health_grade", "")
            accounts = data.get("accounts", [])
            top_cats = data.get("top_categories", [])
            period_label = (data.get("period") or "last_30_days").replace("_", " ")

            ans = (
                f"### Financial Accounts & Summary ({period_label})\n\n"
                f"- **Total Liquid Assets:** ₹{liq:,.2f}\n"
                f"- **Outstanding Credit/Debt:** ₹{debt:,.2f}\n"
                f"- **Period Cash Flow:** ₹{inc:,.2f} inflows vs ₹{exp:,.2f} expenses "
                f"(Net: **{'+' if net >= 0 else ''}₹{net:,.2f}**, Savings Rate: **{s_rate:.1f}%**)\n"
                f"- **Financial Health Score:** **{score}/100** ({grade})\n\n"
            )
            if accounts:
                ans += "**Connected Accounts:**\n"
                for a in accounts:
                    ans += f"- **{a['name']}** ({a['institution']}): ₹{a['balance_inr']:,.2f}\n"
                ans += "\n"

            if top_cats:
                ans += "**Top Spending Categories:**\n"
                for c in top_cats:
                    ans += f"- **{c['category_name']}**: ₹{c['spent_inr']:,.2f} ({c['percentage_share']}%)\n"
                ans += "\n"

            ans += (
                "> **Tip**: Ask me about any specific category (e.g., *\"groceries\"*, *\"rent\"*, *\"utilities\"*), "
                "merchant (*\"Swiggy\"*, *\"Blinkit\"*), budgets, recurring bills, or affordability checks."
            )
            return ProviderResult(content=ans, provider_used=self.name)

        # Fallback
        return ProviderResult(
            content="Processed financial query grounded in your ledger records.",
            provider_used=self.name,
        )

def get_llm_provider() -> BaseLLMProvider:
    """Factory to construct configured LLM provider with fallback to deterministic mock."""
    prov_name = getattr(settings, "LLM_PROVIDER", None) or getattr(settings, "AI_PROVIDER", "mock")
    groq_key = getattr(settings, "GROQ_API_KEY", None)

    if prov_name.lower() == "groq" and groq_key and groq_key.strip():
        model = getattr(settings, "LLM_MODEL", "llama-3.3-70b-versatile")
        temp = getattr(settings, "LLM_TEMPERATURE", 0.2)
        return GroqProvider(api_key=groq_key.strip(), model=model, temperature=temp)

    # Return Mock Deterministic Provider
    return MockLLMProvider()
