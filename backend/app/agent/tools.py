import json
import re
from datetime import datetime, timedelta
from langchain_core.tools import tool
from sqlalchemy.orm import Session
from app.db.models import Interaction, FollowUp, SentimentEnum
from app.db.session import get_db
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
load_dotenv()

# --- Shared LLM fallback helper ---

PRIMARY = os.getenv("MODEL_PRIMARY", "llama-3.3-70b-versatile")
FALLBACK = os.getenv("MODEL_FALLBACK", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


def get_llm(model_name: str = PRIMARY):
  if not GROQ_API_KEY or GROQ_API_KEY == "":
    raise ValueError("GROQ_API_KEY not configured")
  return ChatGroq(model=model_name, api_key=GROQ_API_KEY, temperature=0.1)

# -------------------------------------------------------------------
# HARDCODED APPROVED CLAIMS REFERENCE
# -------------------------------------------------------------------
APPROVED_CLAIMS = {
  "CardiaFlow": [
    "Reduces systolic blood pressure by 8-12 mmHg within 8 weeks",
    "Improves endothelial function in adults with mild hypertension",
    "Safe and well-tolerated in patients over 65",
  ],
  "NeuroVive": [
    "Reduces frequency of migraine attacks by up to 50%",
    "Safe for use in adults with episodic migraine",
    "Does not cause medication-overuse headache with proper dosing",
  ],
  "RespiClear": [
    "Improves FEV1 by 12-15% over baseline",
    "Reduces rescue inhaler use by 30%",
    "Approved for maintenance treatment of asthma in ages 12+",
  ],
}

# -------------------------------------------------------------------
# TOOL 1: log_interaction
# -------------------------------------------------------------------
@tool
def log_interaction(rep_message: str) -> str:
    """Log a new HCP interaction. Input: freeform message from the rep.
    Extracts: hcp_name, interaction_date (natural language to Date),
    sentiment, products_discussed, materials_shared, notes.
    Returns JSON with extracted fields to populate the form.
    Also persists to Postgres.
    """
    db_gen = get_db()
    db: Session = next(db_gen)

    today = datetime.now().date()
    default_date = today.isoformat()

    prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are a CRM data extraction assistant for a life-science field rep.
    Extract structured data from the rep's message.

    Return ONLY valid JSON (no markdown, no backticks). Schema:
    "hcp_name": "Dr. [First Last] or blank",
    "interaction_date": "YYYY-MM-DD (use today if 'today', else parse, or {default_date})",
    "interaction_time": "HH:MM if mentioned, or blank",
    "interaction_type": "In-person call | Virtual call | Email correspondence | Text correspondence",
    "attendees": ["list of attendee names"],
    "topics_discussed": ["list of key topics"],
    "products_discussed": "comma-separated product names or blank",
    "materials_shared": ["brochures, articles, etc"],
    "samples_distributed": ["samples distributed"],
    "observed_sentiment": "positive|neutral|negative",
    "notes": "freeform notes or blank"

    Rules:
    - Arrays empty [] if nothing mentioned. Do NOT invent.
    - If no date, use today: {default_date}. "yesterday" = {(today - timedelta(days=1)).isoformat()}
    - JSON snake_case keys only.
    """),
    ("user", "{rep_message}")
    ])

    try:
        llm = get_llm(PRIMARY)
    except Exception:
        llm = get_llm(FALLBACK)

    chain = prompt | llm
    response = chain.invoke({"rep_message": rep_message})
    raw = response.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()

    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        extracted = {
        "hcp_name": "",
        "interaction_date": default_date,
        "sentiment": "neutral",
        "products_discussed": "",
        "materials_shared": "",
        "notes": rep_message[:300],
        }

    # Persist
    interaction_id = str(__import__("uuid").uuid4())
    new_interaction = Interaction(
    id=interaction_id,
    hcp_name=extracted.get("hcp_name", ""),
    interaction_date=datetime.strptime(extracted.get("interaction_date", default_date), "%Y-%m-%d").date(),
    sentiment=SentimentEnum(extracted.get("sentiment", "neutral")),
    products_discussed=extracted.get("products_discussed", ""),
    materials_shared=extracted.get("materials_shared", ""),
    notes=extracted.get("notes", ""),
    )
    db.add(new_interaction)
    db.commit()

    reply = f"Logged interaction with {extracted.get('hcp_name', 'HCP')} on {extracted.get('interaction_date', today.isoformat())}. Sentiment: {extracted.get('sentiment', 'neutral')}."
    return json.dumps({
    "reply": reply,
    "updated_fields": {k: extracted.get(k) for k in [
        "hcp_name", "interaction_date", "sentiment",
        "products_discussed", "materials_shared", "notes"
    ]},
    "interaction_id": interaction_id,
    })

# -------------------------------------------------------------------
# TOOL 2: edit_interaction
# -------------------------------------------------------------------
@tool
def edit_interaction(correction: str, current_fields_json: str = "{}") -> str:
    """Edit existing interaction fields. Input: correction message + current form state (JSON).
    LLM extracts only the fields that changed, returns JSON with ONLY changed keys.
    Updates Postgres + returns diff to propagate to Redux form.
    """
    db_gen = get_db()
    db: Session = next(db_gen)

    today = datetime.now().date()
    default_date = today.isoformat()

    try:
        current_form = json.loads(current_fields_json) if current_fields_json else {}
    except json.JSONDecodeError:
        current_form = {}

    prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are a CRM data extraction assistant for a life-science field rep.
    Extract structured data from the rep's message.

    Return ONLY valid JSON (no markdown, no backticks). Schema:
    "hcp_name": "Dr. [First Last] or blank",
    "interaction_date": "YYYY-MM-DD (use today if 'today', else parse, or {default_date})",
    "interaction_time": "HH:MM if mentioned, or blank",
    "interaction_type": "In-person call | Virtual call | Email correspondence | Text correspondence",
    "attendees": ["list of attendee names"],
    "topics_discussed": ["list of key topics"],
    "products_discussed": "comma-separated product names or blank",
    "materials_shared": ["brochures, articles, etc"],
    "samples_distributed": ["samples distributed"],
    "observed_sentiment": "positive|neutral|negative",
    "notes": "freeform notes or blank"

    Rules:
    - Arrays empty [] if nothing mentioned. Do NOT invent.
    - If no date, use today: {default_date}. "yesterday" = {(today - timedelta(days=1)).isoformat()}
    - JSON snake_case keys only.
    """),
    ("user", "{rep_message}")
    ])

    try:
        llm = get_llm(PRIMARY)
    except Exception:
        llm = get_llm(FALLBACK)

    chain = prompt | llm
    response = chain.invoke({"rep_message": correction})
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()

    try:
        diff = json.loads(raw)
    except json.JSONDecodeError:
        diff = {}

    if not diff:
        return json.dumps({
        "reply": "No changes detected. Please clarify what you'd like to update.",
        "updated_fields": {},
    })

    # Update DB - find most recent interaction if no id given
    interaction = (
    db.query(Interaction).order_by(Interaction.updated_at.desc()).first()
    )
    if not interaction:
        return json.dumps({
        "reply": "No interaction in session to edit. Please log one first.",
        "updated_fields": {},
    })

    for key, value in diff.items():
        if key == "interaction_date" and value:
            try:
                setattr(interaction, key, datetime.strptime(value, "%Y-%m-%d").date())
            except (ValueError, AttributeError):
                continue
        elif key == "sentiment" and value:
            try:
                setattr(interaction, key, SentimentEnum(value.lower()))
            except ValueError:
                continue
        else:
            if hasattr(interaction, key):
                setattr(interaction, key, value)

    db.commit()

    # Build merged updated_fields for frontend
    updated = {**current_form, **diff}
    reply = f"Updated {len(diff)} field(s): {', '.join(diff.keys())}."
    return json.dumps({
    "reply": reply,
    "updated_fields": updated,
    "interaction_id": interaction.id,
    })

# -------------------------------------------------------------------
# TOOL 3: get_hcp_history
# -------------------------------------------------------------------
@tool
def get_hcp_history(hcp_name: str) -> str:
    """Get past interaction summary for a named HCP.
    Input: HCP name.
    Queries Postgres, LLM summarizes into a brief pre-visit briefing.
    Returns chat text (_does not_ modify form fields).
    """
    db_gen = get_db()
    db: Session = next(db_gen)

    today = datetime.now().date()

    past = (
    db.query(Interaction)
    .filter(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
    .order_by(Interaction.interaction_date.desc())
    .limit(10)
    .all()
    )

    if not past:
        return json.dumps({
        "reply": f"No past interactions found for {hcp_name}.",
        "updated_fields": {},
    })

    rows = [
    f"- {i.interaction_date} | {i.sentiment.value} | Products: {i.products_discussed or 'N/A'} | Notes: {i.notes or 'N/A'}"
    for i in past
    ]
    history_text = "\n".join(rows)

    system_prompt = f"""You are a CRM assistant. Summarize the past HCP interaction history into a brief, actionable pre-visit briefing.

    History:
    {history_text}

    Provide a concise summary highlighting:
    1. Key products discussed and sentiment trends
    2. Outstanding follow-ups or pending actions
    3. Suggested talking points for the next visit
    """

    try:
        llm = get_llm(FALLBACK)
    except Exception:
        llm = get_llm(PRIMARY)

    messages = [SystemMessage(content=system_prompt)]
    summary = llm.invoke(messages).content.strip()

    return json.dumps({
    "reply": f"**Pre-visit briefing for {hcp_name}:**\n\n{summary}",
    "updated_fields": {},
    })

# -------------------------------------------------------------------
# TOOL 4: schedule_follow_up
# -------------------------------------------------------------------
@tool
def schedule_follow_up(message: str) -> str:
    """Extract follow-up date/action from natural language and create a linked follow-up record.
    Input: freeform text like 'circle back in 2 weeks with trial data'.
    Returns: updated form fields + chat reply with scheduled details.
    """
    db_gen = get_db()
    db: Session = next(db_gen)

    today = datetime.now().date()
    default_date = today.isoformat()

    prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are a CRM data extraction assistant for a life-science field rep.
    Extract structured data from the rep's message.

    Return ONLY valid JSON (no markdown, no backticks). Schema:
    "hcp_name": "Dr. [First Last] or blank",
    "interaction_date": "YYYY-MM-DD (use today if 'today', else parse, or {default_date})",
    "interaction_time": "HH:MM if mentioned, or blank",
    "interaction_type": "In-person call | Virtual call | Email correspondence | Text correspondence",
    "attendees": ["list of attendee names"],
    "topics_discussed": ["list of key topics"],
    "products_discussed": "comma-separated product names or blank",
    "materials_shared": ["brochures, articles, etc"],
    "samples_distributed": ["samples distributed"],
    "observed_sentiment": "positive|neutral|negative",
    "notes": "freeform notes or blank"

    Rules:
    - Arrays empty [] if nothing mentioned. Do NOT invent.
    - If no date, use today: {default_date}. "yesterday" = {(today - timedelta(days=1)).isoformat()}
    - JSON snake_case keys only.
    """),
    ("user", "{rep_message}")
    ])

    try:
        llm = get_llm(PRIMARY)
    except Exception:
        llm = get_llm(FALLBACK)

    chain = prompt | llm
    resp = chain.invoke({"rep_message": message})
    raw = resp.content.strip()

    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()

    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        return json.dumps({
        "reply": "Couldn't schedule follow-up. Please specify when and what.",
        "updated_fields": {},
    })

    due_date_str = extracted.get("due_date")
    action = extracted.get("action")
    if not due_date_str or not action:
        return json.dumps({
        "reply": "Couldn't extract a follow-up date/action. Try being more specific, e.g. 'schedule a follow-up in 2 weeks to discuss trial results'.",
        "updated_fields": {},
    })

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        return json.dumps({
        "reply": f"Invalid date extracted: {due_date_str}.",
        "updated_fields": {},
    })

    # Find open interaction to link
    interaction = (
    db.query(Interaction).order_by(Interaction.updated_at.desc()).first()
    )

    follow_up_id = str(__import__("uuid").uuid4())
    if not interaction:
        return json.dumps({"reply": "No interaction found to link follow-up.", "updated_fields": {}})
    fu = FollowUp(
    id=follow_up_id,
    interaction_id=interaction.id,
    due_date=due_date,
    action=action,
    )
    db.add(fu)
    db.commit()

    reply = f"Scheduled follow-up for {due_date.isoformat()}: \"{action}\"."
    return json.dumps({
    "reply": reply,
    "updated_fields": {
        "follow_up_date": due_date.isoformat(),
        "follow_up_action": action,
    },
    "follow_up_id": follow_up_id,
    })

# -------------------------------------------------------------------
# TOOL 5: check_compliance
# -------------------------------------------------------------------
@tool
def check_compliance(interaction_summary: str) -> str:
    """Check claims in an interaction against approved claims reference.
    Input: interaction notes / products_discussed (freeform text).
    Returns: JSON with compliance warnings + form flag update.
    Compliance flag values: "compliant|review_needed".
    """
    today = datetime.now().date()
    default_date = today.isoformat()

    prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are a CRM data extraction assistant for a life-science field rep.
    Extract structured data from the rep's message.

    Return ONLY valid JSON (no markdown, no backticks). Schema:
    "hcp_name": "Dr. [First Last] or blank",
    "interaction_date": "YYYY-MM-DD (use today if 'today', else parse, or {default_date})",
    "interaction_time": "HH:MM if mentioned, or blank",
    "interaction_type": "In-person call | Virtual call | Email correspondence | Text correspondence",
    "attendees": ["list of attendee names"],
    "topics_discussed": ["list of key topics"],
    "products_discussed": "comma-separated product names or blank",
    "materials_shared": ["brochures, articles, etc"],
    "samples_distributed": ["samples distributed"],
    "observed_sentiment": "positive|neutral|negative",
    "notes": "freeform notes or blank"

    Rules:
    - Arrays empty [] if nothing mentioned. Do NOT invent.
    - If no date, use today: {default_date}. "yesterday" = {(today - timedelta(days=1)).isoformat()}
    - JSON snake_case keys only.
    """),
    ("user", "{rep_message}")
    ])

    try:
        llm = get_llm(PRIMARY)
    except Exception:
        llm = get_llm(FALLBACK)

    chain = prompt | llm
    resp = chain.invoke({"rep_message": interaction_summary})
    raw = resp.content.strip()

    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
        "compliant": True,
        "warnings": [],
        "summary": "Compliance check complete.",
    }

    flag = "compliant" if result.get("compliant", True) else "review_needed"

    reply = result.get("summary", "Compliance check complete.")
    if result.get("warnings"):
        reply += "\n\n⚠️ Warnings:\n" + "\n".join(f"- {w}" for w in result["warnings"])

    return json.dumps({
    "reply": reply,
    "updated_fields": {"compliance_flag": flag},
    "compliance_flag": flag,
    })
