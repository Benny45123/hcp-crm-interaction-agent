from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.agent.graph import build_graph
from app.db.models import Base
from app.db.session import engine, get_db
from app.db.models import Interaction, FollowUp, SentimentEnum
from sqlalchemy.orm import Session
from fastapi import Depends
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="HCP CRM Agent API", version="1.0.0")

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-create tables on startup (gracefully handle DB unavailability)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    # Log but don't crash — DB may not be available yet (e.g. Supabase project paused)
    import sys
    print(f"[WARN] Could not auto-migrate tables at startup: {e}", file=sys.stderr)

# Pre-compile LangGraph
graph = build_graph()


# -- Schemas
class ChatRequest(BaseModel):
    message: str
    current_form_state: dict = {}


class ChatResponse(BaseModel):
    assistant_reply: str
    updated_fields: dict
    compliance_flag: str | None = None


# -- Endpoints
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    initial_state = {
        "messages": [{"role": "user", "content": req.message}],
        "current_form_state": req.current_form_state or {},
        "tool_calls": [],
        "updated_fields": {},
        "compliance_flag": None,
    }

    msgs = []
    for m in initial_state["messages"]:
        if m["role"] == "user":
            msgs.append({"role": "user", "content": m["content"]})
        else:
            msgs.append({"role": "assistant", "content": m["content"]})

    state = {
        "messages": msgs,
        "current_form_state": initial_state["current_form_state"],
        "tool_calls": [],
        "updated_fields": {},
        "compliance_flag": None,
    }

    result = graph.invoke(state)

    # Extract assistant reply
    all_msgs = result.get("messages", [])
    assistant_reply = ""
    for m in all_msgs:
        if isinstance(m, dict) and m.get("role") == "assistant":
            assistant_reply = m.get("content", "")
        elif hasattr(m, "content"):
            assistant_reply = getattr(m, "content", "") or assistant_reply

    updated_fields = result.get("updated_fields", {})
    compliance_flag = result.get("compliance_flag")

    return ChatResponse(
        assistant_reply=assistant_reply,
        updated_fields=updated_fields,
        compliance_flag=compliance_flag,
    )


@app.get("/interactions")
def list_interactions(db: Session = Depends(get_db)):
    rows = db.query(Interaction).order_by(Interaction.interaction_date.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "hcp_name": r.hcp_name,
            "interaction_date": r.interaction_date.isoformat(),
            "sentiment": r.sentiment.value,
            "products_discussed": r.products_discussed,
            "materials_shared": r.materials_shared,
            "notes": r.notes,
            "follow_up_date": r.follow_up_date.isoformat() if r.follow_up_date else None,
            "follow_up_action": r.follow_up_action,
            "compliance_flag": r.compliance_flag,
        }
        for r in rows
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
