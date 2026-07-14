# HCP CRM — AI-First Log Interaction Screen

Round 1 Technical Assignment — Life Sciences CRM for field representatives.

---

## Architecture

```
/backend  -> FastAPI + LangGraph + SQLAlchemy + ChatGroq (Groq gemma2-9b-it)
/frontend -> React 18 + Redux Toolkit + Vite
/DB       -> Postgres (Supabase or local Postgres)
Font      -> Google Inter
```

---

## Backend Setup

```bash
cd backend
python3 -m pip install --user -r requirements.txt
cp .env.example .env       # edit: fill GROQ_API_KEY + DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

Required env vars:

| Var | Required | Notes |
|-----|---------|-------|
| `GROQ_API_KEY` | Yes | Get from console.groq.com |
| `DATABASE_URL` | Yes | `postgresql://...` |
| `PORT` | No | default 8000 |
| `FRONTEND_URL` | No | CORS origin, default http://localhost:5173 |
| `MODEL_PRIMARY` | No | default `gemma2-9b-it` |
| `MODEL_FALLBACK` | No | default `llama-3.3-70b-versatile` |

### Endpoint

```
POST /chat
Body: { "message": str, "current_form_state": dict }
Response: { "assistant_reply": str, "updated_fields": dict, "compliance_flag": str | null }
```

### 5 LangGraph Tools

1. **log_interaction** — LLM extracts HCP name, date, sentiment, products, materials, notes from freeform rep text. Writes `Interaction` row. Returns `updated_fields`.
2. **edit_interaction** — LLM diffs correction against `current_form_state`. Updates only changed fields. Merged state returned.
3. **get_hcp_history** — Past `Interaction` rows for named HCP → LLM summarized visit briefing.
4. **schedule_follow_up** — Natural language → due date + action, creates `FollowUp` record, populates Next Follow-up field.
5. **check_compliance** — Compares product claims vs hardcoded approved-claims reference. Sets `compliance_flag = compliant | review_needed`. Warning returned in chat.

### DB Models (SQLAlchemy)

- `Interaction`: id, hcp_name, interaction_date, sentiment, products_discussed, materials_shared, notes, follow_up_date, follow_up_action, compliance_flag, timestamps.
- `FollowUp`: id, interaction_id, due_date, action, status, timestamps.

Auto-migrated on app startup via `Base.metadata.create_all`.

---

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Test Scenarios (from video)

1. Log interaction:
   > "Today I met with Dr. Smith and discussed product X efficacy. The sentiment was positive and I shared the brochures."

2. Edit field:
   > "Sorry, the name was actually Dr. John and the sentiment was negative."

   (Only name and sentiment update — rest stays.)

3. History lookup:
   > "What did we last discuss with Dr. Smith?"

4. Schedule follow-up:
   > "Circle back in two weeks with the trial data."

5. Compliance check:
   > "Check this for off-label claims."

---

## Font

Google Inter loaded via `<link>` in `index.html`. Applied globally via CSS `font-family: Inter`.

## State

- Redux Toolkit store: `interaction` slice (form fields) + `chat` slice (messages / isTyping).
- Form is **read-only** — all mutations flow through `/chat` response → `setFields` dispatch.
- Chat sends `currentFormState` so `edit_interaction` has something to diff against.

---

## Design Principles

- Clean energy / wellness aesthetic — calm greens, whites, elegant typography, generous whitespace.
- Left panel: structured interaction log; right panel: conversational AI.
- Subtle animations on send; typing indicator; pre-built suggestion cards.

---

## License

Assignment submission. Not for redistribution.
