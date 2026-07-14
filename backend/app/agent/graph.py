from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from app.agent.state import AgentState
from app.agent.tools import (
    log_interaction,
    edit_interaction,
    get_hcp_history,
    schedule_follow_up,
    check_compliance,
)
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

# All 5 tools exposed to the LLM
tools = [log_interaction, edit_interaction, get_hcp_history, schedule_follow_up, check_compliance]
TOOL_NAMES = {t.name: t for t in tools}

PRIMARY = os.getenv("MODEL_PRIMARY", "gemma2-9b-it")
FALLBACK = os.getenv("MODEL_FALLBACK", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or ""


def get_llm(model_name: str = PRIMARY):
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")
    return ChatGroq(model=model_name, api_key=GROQ_API_KEY, temperature=0.1)


def _get_user_msg(messages) -> str:
    if not messages:
        return ""
    last = messages[-1]
    if isinstance(last, dict):
        return last.get("content", "") or ""
    return getattr(last, "content", "") or ""


def _get_response_text(resp) -> str:
    content = getattr(resp, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "".join(parts).strip()
    return str(content).strip()


def run_llm_router(messages, current_form_state: dict):
    bound = ", ".join([t.name for t in tools])
    form_json = repr(current_form_state)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f"You are the CRM AI assistant router. Choose EXACTLY ONE tool per turn.

"
            f"Available tools:
"
            f"  log_interaction(rep_message: str) - new HCP interaction
"
            f"  edit_interaction(correction: str, current_fields_json: str) - update fields
"
            f"  get_hcp_history(hcp_name: str) - past interactions summary
"
            f"  schedule_follow_up(message: str) - extract follow-up date/action
"
            f"  check_compliance(interaction_summary: str) - off-label claim check

"
            f"Rules:
"
            f"  1. Logging visit -> log_interaction
"
            f"  2. Correction (actually/update) -> edit_interaction
"
            f"  3. Past interactions question -> get_hcp_history
"
            f"  4. Schedule/circle back -> schedule_follow_up
"
            f"  5. Compliance/off-label check -> check_compliance
"
            f"  6. Greeting/farewell -> plain text, no tool

"
            f"Current form state: {form_json}

"
            f"Return ONLY valid JSON: {{\"action\": \"tool_call\"|\"chat\", \"tool\": \"name\", \"args\": {{...}}}}
"
            f"No markdown. No backticks.
"
            f"Tool names: {bound}",
        ),
        ("user", "{user_msg}"),
    ])

    try:
        llm = get_llm(PRIMARY)
    except Exception:
        llm = get_llm(FALLBACK)

    resp = (prompt | llm).invoke({"user_msg": _get_user_msg(messages)})
    raw = _get_response_text(resp)
    if raw.startswith("```"):
        import re
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    import json
    try:
        return json.loads(raw)
    except Exception:
        return {"action": "chat", "tool": None, "args": {}}


def agent_node(state: AgentState) -> dict:
    routing = run_llm_router(state["messages"], state.get("current_form_state", {}))
    updated = {
        "messages": list(state.get("messages", [])),
        "current_form_state": state.get("current_form_state", {}),
        "tool_calls": [routing],
        "updated_fields": dict(state.get("updated_fields", {})),
        "compliance_flag": state.get("compliance_flag"),
    }

    action = routing.get("action", "chat")
    tool_name = routing.get("tool")
    args = dict(routing.get("args", {}))

    if action != "tool_call" or not tool_name:
        plain = routing.get("args")
        text = "How can I assist you with logging this HCP interaction?"
        if isinstance(plain, dict):
            text = plain.get("message", text)
        updated["messages"] = [*updated["messages"], AIMessage(content=text)]
        return updated

    tool_fn = TOOL_NAMES.get(tool_name)
    if not tool_fn:
        updated["messages"] = [*updated["messages"], AIMessage(content=f"Unknown tool: {tool_name}.")]
        return updated

    if tool_name == "edit_interaction":
        args.setdefault("current_fields_json", __import__("json").dumps(state.get("current_form_state", {})))
    elif tool_name == "log_interaction":
        args["rep_message"] = _get_user_msg(state.get("messages", []))
    elif tool_name == "get_hcp_history":
        args["hcp_name"] = args.get("hcp_name") or "unknown"
    elif tool_name == "check_compliance":
        form = state.get("current_form_state", {})
        notes = form.get("notes", "")
        products = form.get("products_discussed", "")
        args["interaction_summary"] = args.get("interaction_summary") or f"Products: {products}\nNotes: {notes}"

    raw_out = tool_fn.invoke(args)

    import json as _json
    try:
        tool_result = _json.loads(raw_out)
    except Exception:
        tool_result = {"reply": str(raw_out), "updated_fields": {}}

    reply = tool_result.get("reply", "Done.")
    updated["messages"] = [*updated["messages"], AIMessage(content=reply)]
    updated["updated_fields"] = {**updated["updated_fields"], **tool_result.get("updated_fields", {})}
    flag = tool_result.get("compliance_flag")
    if flag:
        updated["compliance_flag"] = flag
    return updated


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.set_entry_point("agent")
    g.add_edge("agent", END)
    return g.compile()


graph = build_graph()
app_graph = build_graph()
