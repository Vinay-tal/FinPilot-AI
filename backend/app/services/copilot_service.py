import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Iterator
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.chat import ChatConversation, ChatMessage
from app.models.user import User
from app.ml.copilot.provider import get_llm_provider, ProviderResult
from app.ml.copilot.guardrails import (
    sanitize_user_input,
    wrap_untrusted_data,
    check_out_of_scope,
    SYSTEM_FINANCIAL_COPILOT_PROMPT,
)
from app.ml.copilot.tools import (
    AVAILABLE_TOOLS_SPEC,
    QueryTransactionsInput,
    execute_query_transactions,
    ComparePeriodsInput,
    execute_compare_periods,
    GetRecurringInput,
    execute_get_recurring,
    GetBudgetAndGoalsInput,
    execute_get_budget_and_goals,
    GetCashflowForecastInput,
    execute_get_forecast,
    SimulateScenarioInput,
    execute_simulate_scenario,
    GetHealthScoreInput,
    execute_get_financial_health_score,
    GetRecommendationsInput,
    execute_get_personalized_recommendations,
)

logger = logging.getLogger(__name__)

def list_conversations(db: Session, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """List all chat conversations belonging to the user."""
    convs = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user_id)
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )

    result = []
    for c in convs:
        msg_count = db.query(sa.func.count(ChatMessage.id)).filter(ChatMessage.conversation_id == c.id).scalar() or 0
        last_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == c.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        result.append({
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
            "message_count": msg_count,
            "last_message_preview": (last_msg.content[:80] + "...") if last_msg else "New conversation",
        })

    return result

def get_or_create_default_conversation(db: Session, user_id: uuid.UUID) -> ChatConversation:
    """Get active conversation or seed new default conversation."""
    conv = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user_id)
        .order_by(ChatConversation.updated_at.desc())
        .first()
    )
    if not conv:
        conv = ChatConversation(
            user_id=user_id,
            title="Financial Copilot Discussion",
        )
        db.add(conv)
        db.flush()

        # Seed welcome turn
        user = db.query(User).filter(User.id == user_id).first()
        user_name = user.full_name if user else "there"
        welcome_msg = ChatMessage(
            conversation_id=conv.id,
            user_id=user_id,
            role="ASSISTANT",
            content=(
                f"Hello {user_name}! I am your FinPilot AI Copilot. I am connected directly to your "
                f"financial accounts, budget pacing, recurring mandates, and cash-flow forecast models.\n\n"
                f"You can ask me questions like:\n"
                f"- *How much did I spend on food this month?*\n"
                f"- *Which categories increased the most compared with last month?*\n"
                f"- *Can I afford a ₹15,000 purchase without dropping below my emergency reserve?*\n"
                f"- *Why does the system predict a low balance near month-end?*\n"
                f"- *Where could I reduce spending by ₹2,000 next month?*\n"
                f"- *What recurring payments are due soon?*\n"
                f"- *How much could I save in six months under different spending assumptions?*"
            ),
            provider_used="finpilot-welcome",
        )
        db.add(welcome_msg)
        db.flush()

    return conv

def create_conversation(db: Session, user_id: uuid.UUID, title: Optional[str] = None) -> ChatConversation:
    """Create an explicitly new conversation."""
    conv = ChatConversation(
        user_id=user_id,
        title=title or "New Discussion",
    )
    db.add(conv)
    db.flush()

    user = db.query(User).filter(User.id == user_id).first()
    user_name = user.full_name if user else "there"
    welcome_msg = ChatMessage(
        conversation_id=conv.id,
        user_id=user_id,
        role="ASSISTANT",
        content=f"Hello {user_name}! What financial question can I help you investigate today?",
        provider_used="finpilot-welcome",
    )
    db.add(welcome_msg)
    db.flush()
    return conv

def rename_conversation(db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID, new_title: str) -> ChatConversation:
    """Rename conversation title with tenant authorization."""
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user_id,
    ).first()
    if not conv:
        raise ValueError("Conversation not found or unauthorized.")
    conv.title = new_title.strip()[:200]
    db.flush()
    return conv

def delete_conversation(db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID) -> bool:
    """Delete a conversation with tenant authorization."""
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user_id,
    ).first()
    if not conv:
        return False
    db.delete(conv)
    db.flush()
    return True

def get_conversation_messages(db: Session, user_id: uuid.UUID, conversation_id: uuid.UUID) -> List[ChatMessage]:
    """Retrieve message history for a conversation."""
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user_id,
    ).first()
    if not conv:
        raise ValueError("Conversation not found or unauthorized.")

    return db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.user_id == user_id,
    ).order_by(ChatMessage.created_at.asc()).all()

def dispatch_tool(db: Session, user_id: uuid.UUID, tool_name: str, arguments_json: str) -> Dict[str, Any]:
    """Validate tool input with Pydantic and execute deterministically for authorized user."""
    try:
        args = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
    except Exception:
        args = {}

    if tool_name == "query_aggregate_transactions":
        validated = QueryTransactionsInput(**args)
        return execute_query_transactions(db, user_id, validated)
    elif tool_name == "compare_time_periods":
        validated = ComparePeriodsInput(**args)
        return execute_compare_periods(db, user_id, validated)
    elif tool_name == "get_recurring_payments":
        validated = GetRecurringInput(**args)
        return execute_get_recurring(db, user_id, validated)
    elif tool_name == "get_budget_and_goals_progress":
        validated = GetBudgetAndGoalsInput(**args)
        return execute_get_budget_and_goals(db, user_id, validated)
    elif tool_name == "get_cashflow_forecast":
        validated = GetCashflowForecastInput(**args)
        return execute_get_forecast(db, user_id, validated)
    elif tool_name == "simulate_financial_scenario":
        validated = SimulateScenarioInput(**args)
        return execute_simulate_scenario(db, user_id, validated)
    elif tool_name == "get_financial_health_score":
        validated = GetHealthScoreInput(**args)
        return execute_get_financial_health_score(db, user_id, validated)
    elif tool_name == "get_personalized_recommendations":
        validated = GetRecommendationsInput(**args)
        return execute_get_personalized_recommendations(db, user_id, validated)
    else:
        raise ValueError(f"Unauthorized or unknown tool: {tool_name}")

def extract_citations_and_metadata(tool_name: str, tool_result: Dict[str, Any]) -> Dict[str, Any]:
    """Construct structured citations and facts vs estimates categorization."""
    citations = []
    facts = []
    estimates = []
    scenarios = []
    scenario_card = None

    if tool_name == "query_aggregate_transactions":
        tot = tool_result.get("total_amount_inr", 0)
        cat = tool_result.get("category_name", "Transactions")
        cnt = tool_result.get("transaction_count", 0)
        citations.append({
            "source": "TRANSACTIONS_LEDGER",
            "title": f"{cat} Expenditure",
            "value": f"₹{tot:,.2f}",
            "detail": f"{cnt} settled transactions in period",
        })
        facts.append(f"Verified ₹{tot:,.2f} settled across {cnt} transactions in {cat}.")

    elif tool_name == "compare_time_periods":
        c_tot = tool_result.get("current_total_expenses_inr", 0)
        p_tot = tool_result.get("previous_total_expenses_inr", 0)
        pct = tool_result.get("net_percentage_change", 0)
        citations.append({
            "source": "MOM_EXPENSE_COMPARISON",
            "title": "Current vs Previous Expenses",
            "value": f"₹{c_tot:,.2f} vs ₹{p_tot:,.2f}",
            "detail": f"{pct:+.1f}% month-over-month shift",
        })
        facts.append(f"Historical monthly expenses changed by {pct:+.1f}% compared to previous month.")

    elif tool_name == "get_recurring_payments":
        bills = tool_result.get("total_upcoming_bills_inr", 0)
        inc = tool_result.get("total_upcoming_income_inr", 0)
        citations.append({
            "source": "RECURRING_MANDATES",
            "title": "Upcoming 30d Commitments",
            "value": f"₹{bills:,.2f}",
            "detail": f"Against ₹{inc:,.2f} expected income",
        })
        facts.append(f"Upcoming recurring obligations total ₹{bills:,.2f} due within 30 days.")

    elif tool_name == "get_cashflow_forecast":
        end_bal = tool_result.get("predicted_end_balance_inr", 0)
        min_dip = tool_result.get("minimum_projected_dip_inr", 0)
        citations.append({
            "source": "FORECAST_ENGINE",
            "title": "Predicted Month-End Cash",
            "value": f"₹{end_bal:,.2f}",
            "detail": f"Projected minimum dip point: ₹{min_dip:,.2f}",
        })
        estimates.append(f"Ridge ML calendar model projects balance will dip to ₹{min_dip:,.2f} before salary credit.")

    elif tool_name == "simulate_financial_scenario":
        sc_type = tool_result.get("scenario")
        if sc_type == "AFFORD_PURCHASE":
            amt = tool_result.get("purchase_amount_inr", 0)
            verdict = tool_result.get("verdict_title", "")
            post_dip = tool_result.get("projected_post_purchase_min_dip_inr", 0)
            citations.append({
                "source": "SCENARIO_SIMULATOR",
                "title": f"Purchase Affordability (₹{amt:,.0f})",
                "value": verdict,
                "detail": f"Post-purchase minimum buffer: ₹{post_dip:,.2f}",
            })
            scenarios.append(f"Simulated purchase of ₹{amt:,.0f} results in minimum buffer of ₹{post_dip:,.2f}.")
            scenario_card = {
                "type": "AFFORDABILITY",
                "title": f"Affordability Verdict: ₹{amt:,.0f} Purchase",
                "verdict": tool_result.get("verdict"),
                "badge": tool_result.get("verdict_title"),
                "current_liquid_inr": tool_result.get("current_liquid_inr"),
                "post_purchase_min_dip_inr": post_dip,
                "reserve_threshold_inr": tool_result.get("reserve_threshold_inr"),
                "recommendation": tool_result.get("recommendation"),
            }
        elif sc_type == "REDUCE_SPENDING":
            target = tool_result.get("target_reduction_inr", 0)
            alloc = tool_result.get("recommended_allocation", [])
            citations.append({
                "source": "SCENARIO_SIMULATOR",
                "title": f"Spending Reduction Plan",
                "value": f"-₹{target:,.0f}/mo",
                "detail": f"Allocated across {len(alloc)} discretionary categories",
            })
            scenarios.append(f"Allocated target cut of ₹{target:,.0f} across discretionary categories.")
            scenario_card = {
                "type": "SPENDING_REDUCTION",
                "title": f"Monthly Optimization: Save ₹{target:,.0f}",
                "target_reduction_inr": target,
                "projected_monthly_savings_inr": tool_result.get("projected_monthly_savings_inr"),
                "projected_savings_rate_pct": tool_result.get("projected_savings_rate_pct"),
                "allocation": alloc,
            }
        elif sc_type == "FUTURE_SAVINGS":
            months = tool_result.get("target_months", 6)
            wealth = tool_result.get("total_wealth_created_inr", 0)
            opt_cum = tool_result.get("optimized_cumulative_savings_inr", 0)
            citations.append({
                "source": "SCENARIO_SIMULATOR",
                "title": f"{months}-Month Savings Projection",
                "value": f"₹{opt_cum:,.2f}",
                "detail": f"+₹{wealth:,.2f} additional wealth created",
            })
            scenarios.append(f"Projected {months}-month cumulative savings at ₹{opt_cum:,.2f} under savings boost.")
            scenario_card = {
                "type": "SAVINGS_HORIZON",
                "title": f"{months}-Month Accumulated Wealth Projection",
                "months": months,
                "baseline_cumulative_inr": tool_result.get("baseline_cumulative_savings_inr"),
                "optimized_cumulative_inr": opt_cum,
                "additional_wealth_inr": wealth,
                "progression": tool_result.get("monthly_progression", []),
            }

    elif tool_name == "get_financial_health_score":
        score = tool_result.get("overall_score", 0)
        grade = tool_result.get("grade", "Fair")
        citations.append({
            "source": "HEALTH_SCORE_ENGINE",
            "title": f"Health Score: {score}/100 ({grade})",
            "value": f"{score}/100",
            "detail": f"{len(tool_result.get('factors', []))} factors evaluated",
        })
        facts.append(f"Financial Health Score calculated at {score}/100 ({grade}) using normalized personal factors.")

    elif tool_name == "get_personalized_recommendations":
        recs = tool_result.get("recommendations", [])
        citations.append({
            "source": "RECOMMENDATION_ENGINE",
            "title": f"Active Recommendations ({len(recs)})",
            "value": f"{len(recs)} Suggestions",
            "detail": "Prioritized deterministic spending and reserve optimizations",
        })
        for r in recs[:3]:
            facts.append(f"Recommendation: {r.get('title')} (Est. impact: ₹{r.get('estimated_impact_inr', 0):,.0f})")

    return {
        "citations": citations,
        "facts_vs_estimates": {
            "retrieved_facts": facts,
            "model_estimates": estimates,
            "hypothetical_scenarios": scenarios,
        },
        "scenario_card": scenario_card,
    }

def generate_followup_suggestions(query: str, tool_name: Optional[str] = None) -> List[str]:
    """Generate dynamic follow-up prompts based on the current context."""
    q = query.lower()
    if "food" in q or "dining" in q:
        return [
            "Which categories increased the most compared with last month?",
            "Where could I reduce spending by ₹2,000 next month?",
            "What is my current budget pacing for Food & Dining?",
        ]
    elif "afford" in q or "buy" in q:
        return [
            "Where can I reduce expenses to afford this faster?",
            "Why does the system predict a low balance near month-end?",
            "What recurring payments are due before my next salary?",
        ]
    elif "predict" in q or "low balance" in q or "forecast" in q:
        return [
            "What recurring payments are due soon?",
            "Can I afford a ₹15,000 purchase without dropping below my emergency reserve?",
            "How much could I save in six months under different spending assumptions?",
        ]
    elif "recurring" in q or "bill" in q:
        return [
            "Why does the system predict a low balance near month-end?",
            "How much did I spend on food this month?",
            "Where could I reduce spending by ₹2,000 next month?",
        ]
    elif "increase" in q or "last month" in q:
        return [
            "Where could I reduce spending by ₹2,000 next month?",
            "Can I afford a ₹15,000 purchase without dropping below my emergency reserve?",
            "How much did I spend on food this month?",
        ]
    else:
        return [
            "How much did I spend on food this month?",
            "Can I afford a ₹15,000 purchase without dropping below my emergency reserve?",
            "Why does the system predict a low balance near month-end?",
            "What recurring payments are due soon?",
        ]

def process_copilot_turn(
    db: Session,
    user_id: uuid.UUID,
    conversation_id: Optional[uuid.UUID],
    query: str,
) -> Dict[str, Any]:
    """
    Main orchestration function for Copilot turn:
    1. Sanitize query & check guardrails.
    2. Save user turn.
    3. Invoke LLM provider with tools.
    4. Execute tools deterministically.
    5. Generate final narrative & metadata.
    6. Persist assistant turn and return response.
    """
    # 1. Guardrails & sanitization
    clean_query = sanitize_user_input(query)
    if not clean_query:
        raise ValueError("Query cannot be empty.")

    out_of_scope_msg = check_out_of_scope(clean_query)

    # 2. Resolve conversation
    if conversation_id:
        conv = db.query(ChatConversation).filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
        ).first()
        if not conv:
            raise ValueError("Conversation not found or unauthorized.")
    else:
        conv = get_or_create_default_conversation(db, user_id)

    # Update conversation title if default and 1st user message
    if conv.title in ["Financial Copilot Discussion", "New Discussion"]:
        conv.title = clean_query[:50] + ("..." if len(clean_query) > 50 else "")

    # Save user message
    user_msg = ChatMessage(
        conversation_id=conv.id,
        user_id=user_id,
        role="USER",
        content=clean_query,
        provider_used="user",
    )
    db.add(user_msg)
    db.flush()

    # Handle out-of-scope early exit
    if out_of_scope_msg:
        bot_msg = ChatMessage(
            conversation_id=conv.id,
            user_id=user_id,
            role="ASSISTANT",
            content=out_of_scope_msg,
            provider_used="finpilot-guardrails",
        )
        db.add(bot_msg)
        db.flush()
        return {
            "conversation_id": str(conv.id),
            "message_id": str(bot_msg.id),
            "answer": out_of_scope_msg,
            "provider_used": "finpilot-guardrails",
            "citations": [],
            "facts_vs_estimates": {
                "retrieved_facts": [],
                "model_estimates": [],
                "hypothetical_scenarios": [],
            },
            "scenario_card": None,
            "suggested_followups": [
                "How much did I spend on food this month?",
                "Can I afford a ₹15,000 purchase without dropping below my emergency reserve?",
                "What recurring payments are due soon?",
            ],
        }

    # 3. Prepare messages for provider
    past_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(10)
        .all()
    )

    llm_history = []
    for m in past_messages:
        llm_history.append({"role": m.role.lower(), "content": m.content})

    provider = get_llm_provider()

    # Call provider with available tools
    initial_res = provider.generate(
        messages=llm_history,
        tools=AVAILABLE_TOOLS_SPEC,
        system_prompt=SYSTEM_FINANCIAL_COPILOT_PROMPT,
    )

    all_citations = []
    facts_vs_estimates = {"retrieved_facts": [], "model_estimates": [], "hypothetical_scenarios": []}
    scenario_card = None
    last_tool_executed = None

    # Check if provider requested tool calls
    if initial_res.tool_calls:
        for tc in initial_res.tool_calls:
            fn = tc.get("function", {})
            t_name = fn.get("name")
            t_args = fn.get("arguments", "{}")
            last_tool_executed = t_name

            try:
                tool_output = dispatch_tool(db, user_id, t_name, t_args)
            except Exception as e:
                logger.error(f"Error executing tool {t_name}: {e}", exc_info=True)
                tool_output = {"error": f"Failed to execute tool {t_name}: {str(e)}"}

            # Extract citations and metadata
            meta = extract_citations_and_metadata(t_name, tool_output)
            all_citations.extend(meta["citations"])
            facts_vs_estimates["retrieved_facts"].extend(meta["facts_vs_estimates"]["retrieved_facts"])
            facts_vs_estimates["model_estimates"].extend(meta["facts_vs_estimates"]["model_estimates"])
            facts_vs_estimates["hypothetical_scenarios"].extend(meta["facts_vs_estimates"]["hypothetical_scenarios"])
            if meta["scenario_card"]:
                scenario_card = meta["scenario_card"]

            # Append tool output to history
            llm_history.append({
                "role": "tool",
                "tool_call_id": tc.get("id", "call_1"),
                "name": t_name,
                "content": json.dumps(tool_output),
            })

        # Synthesize final answer from tool output
        final_res = provider.generate(
            messages=llm_history,
            system_prompt=SYSTEM_FINANCIAL_COPILOT_PROMPT,
        )
        final_answer = final_res.content or "Analysis completed successfully based on your financial records."
        provider_name = final_res.provider_used
    else:
        final_answer = initial_res.content or "Here is what I found in your records."
        provider_name = initial_res.provider_used

    # Build suggested follow-ups
    followups = generate_followup_suggestions(clean_query, last_tool_executed)

    # Save assistant turn to database
    bot_msg = ChatMessage(
        conversation_id=conv.id,
        user_id=user_id,
        role="ASSISTANT",
        content=final_answer,
        provider_used=provider_name,
        citations_json=json.dumps(all_citations),
    )
    db.add(bot_msg)
    db.flush()

    return {
        "conversation_id": str(conv.id),
        "message_id": str(bot_msg.id),
        "answer": final_answer,
        "provider_used": provider_name,
        "citations": all_citations,
        "facts_vs_estimates": facts_vs_estimates,
        "scenario_card": scenario_card,
        "suggested_followups": followups,
    }
