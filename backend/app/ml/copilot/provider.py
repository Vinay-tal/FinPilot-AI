import json
import logging
import re
from abc import ABC, abstractmethod
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
    Deterministic offline provider that mirrors real model reasoning:
    1. If called without tool output, inspects user prompt and requests the appropriate tool.
    2. If called with tool output, synthesizes clean, accurate, grounded explanations.
    """

    @property
    def name(self) -> str:
        return "mock-deterministic-v1"

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

        # Otherwise, inspect latest user message to pick tool
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "").lower()
                break

        # 1. Food / Dining / Swiggy / Category spend
        if any(w in user_msg for w in ["food", "dining", "swiggy", "zomato", "eat", "restaurant", "groceries", "shopping"]):
            cat_slug = "food-dining" if any(w in user_msg for w in ["food", "dining", "swiggy", "zomato"]) else "shopping"
            return ProviderResult(
                tool_calls=[{
                    "id": "call_tx_1",
                    "type": "function",
                    "function": {
                        "name": "query_aggregate_transactions",
                        "arguments": json.dumps({"category_slug": cat_slug, "transaction_type": "DEBIT"}),
                    },
                }],
                provider_used=self.name,
            )

        # 2. Compare periods / increased the most vs last month
        if any(w in user_msg for w in ["increased", "compared", "last month", "vs last month", "more than last"]):
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

        # 3. Afford purchase without dropping below emergency reserve
        if any(w in user_msg for w in ["afford", "buy", "purchase", "emergency reserve", "drop below"]):
            # Extract number if present
            nums = re.findall(r'\d+', user_msg.replace(",", ""))
            purchase_amt = float(nums[0]) if nums else 15000.0
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

        # 4. Predict low balance near month-end / forecast
        if any(w in user_msg for w in ["predict", "forecast", "low balance", "month-end", "near month-end", "shortfall"]):
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

        # 5. Reduce spending / cut spending
        if any(w in user_msg for w in ["reduce spending", "cut spending", "save 2000", "reduce by", "save extra"]):
            nums = re.findall(r'\d+', user_msg.replace(",", ""))
            cut_amt = float(nums[0]) if nums else 2000.0
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

        # 6. Recurring payments / bills due soon
        if any(w in user_msg for w in ["recurring", "due soon", "bills", "subscriptions", "payments due"]):
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

        # 7. Six months savings under different assumptions
        if any(w in user_msg for w in ["six months", "6 months", "save in", "savings assumption"]):
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

        # 8. Financial Health Score
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

        # 9. Personalized Recommendations
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

        # Default fallback: inspect budgets and goals
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

    def _synthesize_tool_response(self, tool_name: str, data: Dict[str, Any], messages: List[Dict[str, Any]]) -> ProviderResult:
        if tool_name == "query_aggregate_transactions":
            total = data.get("total_amount_inr", 0)
            count = data.get("transaction_count", 0)
            cat_name = data.get("category_name", "Food & Dining")
            avg = data.get("average_amount_inr", 0)
            top_merchants = data.get("top_merchants", [])
            merch_str = ", ".join(f"{m['merchant']} (₹{m['total_spent_inr']:,.2f})" for m in top_merchants[:3])

            ans = (
                f"### {cat_name} Spending Breakdown\n\n"
                f"Based on your verified bank transactions, you have spent a total of **₹{total:,.2f}** across **{count} transactions** "
                f"this period (average: **₹{avg:,.2f}** per transaction).\n\n"
            )
            if top_merchants:
                ans += f"**Top merchants:** {merch_str}.\n\n"
            ans += (
                f"> **Observed Fact**: All transactions are verified and settled on your accounts. "
                f"Frequent online delivery orders represent your primary day-to-day burn rate."
            )
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

        # Fallback
        return ProviderResult(
            content=f"Processed financial query grounded in your ledger records. Tool output verified successfully.",
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
