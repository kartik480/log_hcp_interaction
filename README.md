# AI-First CRM - HCP Log Interaction Module

AI-first CRM module for life-science field reps to log Healthcare Professional (HCP) interactions using either a structured form or conversational AI chat.

This project satisfies the requested stack:
- `React` + `Redux Toolkit` frontend
- `FastAPI` backend
- `LangGraph` agent workflows
- LLM via `OpenRouter` (configurable model)
- `MySQL` persistence (SQLAlchemy)

## What It Does

- Log HCP interactions from:
  - structured form input
  - AI chat prompt
- Auto-extract and map conversation into form fields:
  - HCP name, interaction type, attendees
  - topics discussed, sentiment, outcomes
  - follow-up actions, materials, samples
- Run compliance checks and follow-up planning via LangGraph tools
- Save, edit, and fetch interactions from MySQL

## Project Structure

```text
projectTask/
  frontend/                      # React + Redux UI
  backend/
    app/
      agent/                     # LangGraph workflows + tools
      routers/                   # FastAPI endpoints
      services/                  # DB service layer
      schemas/                   # Pydantic request/response models
      models.py                  # SQLAlchemy models
      db.py                      # DB engine/session/init
  backend/sql/schema.sql         # MySQL schema
  docker-compose.yml             # MySQL container setup
```

## LangGraph Workflows

Three workflows are configured:

1. `backend/app/agent/graph.py`  
   Parse chat prompt -> structured patch for form fields.

2. `backend/app/agent/workflows.py` (`log_graph`)  
   Summarize -> compliance guard -> persist interaction -> sync tasks.

3. `backend/app/agent/workflows.py` (`edit_graph`)  
   Compliance guard -> persist audited edit revision.

## LangGraph Tools

Implemented in `backend/app/agent/tools.py`:
- `log_interaction`
- `edit_interaction`
- `fetch_hcp_context`
- `validate_materials_and_samples`
- `compliance_guard`
- `plan_follow_ups`
- `sync_calendar_tasks`

## API Endpoints

Base router: `/interactions`

- `POST /interactions/parse-chat`
- `POST /interactions/log`
- `PATCH /interactions/{interaction_id}`
- `GET /interactions/{interaction_id}`

Health:
- `GET /health`

OpenAPI:
- `http://127.0.0.1:8000/docs`

## Prerequisites

- Node.js 20+
- Python 3.11+
- MySQL 8+ (or Docker Desktop)
- OpenRouter API key: `https://openrouter.ai/`

## Environment Variables

Create `backend/.env` from `backend/.env.example`.

Required/important:
- `DATABASE_URL=mysql+pymysql://crm_user:crm_pass@127.0.0.1:3306/hcp_crm`
- `OPENROUTER_API_KEY=<your_openrouter_key>`
- `OPENROUTER_MODEL_PRIMARY=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`
- `OPENROUTER_MODEL_FALLBACK=meta-llama/llama-3.3-70b-instruct:free`
- `API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

## Run With Docker MySQL (Recommended)

From repo root:

```powershell
docker compose up -d mysql
```

Then backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open:
- Frontend: `http://127.0.0.1:5173` (or next free Vite port)
- Backend docs: `http://127.0.0.1:8000/docs`

## Run With Local MySQL (No Docker)

1. Ensure MySQL server is running on `127.0.0.1:3306`
2. Create DB/user matching `DATABASE_URL`
3. Execute `backend/sql/schema.sql`
4. Start backend + frontend as above

## Notes

- If the AI assistant only fills `topics_discussed`, backend is likely running without `OPENROUTER_API_KEY` and falling back to stub extraction.
- If backend logs show MySQL connection refused, start MySQL and verify `DATABASE_URL`.
- Vite may auto-shift to `5174/5175` if `5173` is already occupied.

## License

Starter template for assignment/demo use.
