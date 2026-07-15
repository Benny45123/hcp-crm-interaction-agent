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
import re
import json as _json
from dotenv import load_dotenv

load_dotenv()

# All 5 tools exposed to the LLM
tools = [log_interaction, edit_interaction, get_hcp_history, schedule_follow_up, check_compliance]
TOOL_NAMES = {t.name: t for t in tools}

PRIMARY = os.getenv("MODEL_PRIMARY", "llama-3.3-70b-versatile")
FALLBACK = os.getenv("MODEL_FALLBACK", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


def get_llm(model_name: str = PRIMARY):
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")
    return ChatGroq(model=model_name, api_key=GROQ_API_KEY, temperature=0.1)  # type: ignore[arg-type]


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


def _build_system_prompt(current_form_state: dict, bound: str) -> str:
    form_json_segment = _json.dumps(current_form_state) if current_form_state else "(empty)"
    return (
        "You are the CRM AI assistant router for a pharmaceutical field rep app.\n\n"
        "Available tools:\n"
        " - log_interaction(rep_message: str) -> new HCP interaction\n"
        " - edit_interaction(correction: str, current_fields_json: str) -> update fields\n"
        " - get_hcp_history(hcp_name: str) -> past interactions summary\n"
        " - schedule_follow_up(message: str) -> extract follow-up date/action\n"
        " - check_compliance(interaction_summary: str) -> off-label claim check\n\n"
        "Routing rules (be very strict):\n"
        ' 1. If rep message describes a new visit or interaction details -> action "tool_call", tool "log_interaction"\n'
        ' 2. If rep message says "actually", "update", "correction", "instead", "no" (fixing an entry) -> action "tool_call", tool "edit_interaction"\n'
        ' 3. If rep asks about past visits for a named HCP -> action "tool_call", tool "get_hcp_history"\n'
        ' 4. If rep says "follow up", "schedule", "circle back", "remind", "next week" -> action "tool_call", tool "schedule_follow_up"\n'
        ' 5. If rep asks "is this compliant", "off-label", "any warnings", "check" -> action "tool_call", tool "check_compliance"\n'
        ' 6. If rep says hi/bye/thanks/hello/good morning with no substantive details -> action "chat"\n\n'
        f"Current form state JSON: {form_json_segment}\n\n"
        "Respond with EXACTLY this JSON structure and nothing else:\n"
        '{"action": "tool_call" or "chat", "tool": "tool_name_or_null", "args": {"key": "value"}}\n'
        "No markdown. No code fences. No explanation.\n"
        f"Valid tool names: {bound}\n"
    )


def run_llm_router(messages, current_form_state: dict):
    bound = ", ".join([t.name for t in tools])
    system_text = _build_system_prompt(current_form_state, bound)
    llm_messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": _get_user_msg(messages)},
    ]
    try:
        llm = get_llm(PRIMARY)
    except Exception:
        llm = get_llm(FALLBACK)
    resp = llm.invoke(llm_messages)
    raw = _get_response_text(resp)
    print(f"[ROUTER RAW LLM OUTPUT]: {raw!r}")
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        parsed = _json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Not a dict")
        return parsed
    except Exception:
        pass
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
        args.setdefault("current_fields_json", _json.dumps(state.get("current_form_state", {})))
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
