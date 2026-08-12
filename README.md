# AI Job Application Automation System

A full-stack AI-powered job application automation system with a React frontend dashboard and FastAPI backend.

## Architecture

- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
- **Backend**: Python FastAPI with async SQLAlchemy
- **Database**: Supabase Postgres
- **File Storage**: Supabase Storage
- **LLM**: OpenRouter (poolside/laguna-s-2.1:free)
- **Deployment**: Vercel (frontend) + Railway (backend)

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12+
- Supabase account
- Render.com account (or other Python hosting)

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Backend Development
```bash
cd backend
pip install -r api/requirements.txt
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### Environment Variables
Copy `.env.example` from backend and configure:
```bash
cp backend/.env.example backend/.env
```

Update with your Supabase credentials and LLM API keys.

### Model Configuration

The LLM model is configured once via the `ANTHROPIC_MODEL` environment variable:

| Source | Where |
|--------|-------|
| `.claude/settings.json` (`env.ANTHROPIC_MODEL`) | **Primary** — used by Claude Code for all backend and frontend operations |
| `backend/.env` (`ANTHROPIC_MODEL`) | Used at runtime / in deployment |

The backend (`llm/client.py`) and frontend (`LLMSettingsForm.tsx`) both read this variable directly. `LLM_MODEL` is kept as a legacy alias. To switch models, edit `ANTHROPIC_MODEL` in `.claude/settings.json` — no code changes needed.

## Deployment

### Supabase Setup
1. Create a project at [supabase.com](https://supabase.com)
2. Run the migrations from `supabase/migrations/`
3. Create a `resumes` storage bucket
4. Copy the project URL, anon key, and database connection string

### Frontend Deployment (Vercel)
```bash
cd frontend
vercel --prod
```
Set environment variables in Vercel project settings:
- `VITE_API_URL` — backend URL on Render.com
- `VITE_SUPABASE_URL` — Supabase project URL
- `VITE_SUPABASE_ANON_KEY` — Supabase anon key
- `ANTHROPIC_MODEL` — LLM model identifier (e.g. `poolside/laguna-s-2.1:free`). See [Model Configuration](#model-configuration) below.

### Backend Deployment (Railway)
1. Create a project at [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Railway auto-detects `railway.json` and uses the Dockerfile
4. Set environment variables:
   - `DATABASE_URL` — Supabase Postgres URL
   - `SUPABASE_URL` — Supabase project URL
   - `SUPABASE_ANON_KEY` — Supabase anon key
   - `LLM_API_KEY` — OpenRouter API key
   - `LLM_BASE_URL` — `https://openrouter.ai/api/v1`
   - `ANTHROPIC_MODEL` — LLM model identifier (e.g. `poolside/laguna-s-2.1:free`). Change this in `.claude/settings.json` to update the model everywhere.
   - `CORS_ORIGINS` — your Vercel frontend URL

## Project Structure
```
.
├── frontend/          # React/Vite frontend
│   ├── src/
│   │   ├── pages/     # Route pages (Dashboard, Profile, Jobs, etc.)
│   │   ├── components/ # Reusable UI components
│   │   ├── hooks/     # React hooks (API, WebSocket)
│   │   ├── services/  # API services (axios, websocket, supabase)
│   │   ├── store/     # Zustand state management
│   │   └── types/     # Shared TypeScript types
├── backend/           # Python backend
│   ├── api/           # FastAPI server
│   │   ├── routes/    # API route handlers
│   │   └── schemas.py # Pydantic response models
│   ├── agents/        # AI agents (Profile, Discovery, Matching, Resume)
│   ├── resume/        # Resume parsing, customization, validation
│   ├── job_sources/   # Job source integrations
│   ├── llm/           # LLM client and prompts
│   ├── database/      # SQLAlchemy models and repositories
│   └── orchestration/ # Pipeline orchestration
├── supabase/
│   └── migrations/    # Database migration SQL files
└── vercel.json        # Vercel frontend config
```

## License
MIT