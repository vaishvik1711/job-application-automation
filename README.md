# AI Job Application Automation System

A full-stack AI-powered job application automation system with a React frontend dashboard and FastAPI backend.

## Architecture

- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
- **Backend**: Python FastAPI with async SQLAlchemy
- **Database**: Supabase Postgres
- **File Storage**: Supabase Storage
- **LLM**: OpenRouter (poolside/laguna-s-2.1:free)
- **Deployment**: Cloudflare Pages (frontend) + Railway (backend)

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12+
- Supabase account
- Railway account (for backend hosting)

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

### Frontend Deployment (Cloudflare Pages)
Deploy via the Cloudflare dashboard (see [DEPLOYMENT.md](DEPLOYMENT.md) for full step-by-step) or:
```bash
cd frontend
npx wrangler pages deploy dist
```
Set environment variables in Cloudflare Pages project settings:
- `VITE_API_URL` — backend URL on Railway
- `VITE_SUPABASE_URL` — Supabase project URL
- `VITE_SUPABASE_ANON_KEY` — Supabase anon key
- `VITE_ANTHROPIC_MODEL` — LLM model identifier (e.g. `poolside/laguna-s-2.1:free`). See [Model Configuration](#model-configuration) below.

### Backend Deployment (Railway)
1. Create a project at [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Railway auto-detects `railway.json` and uses the Dockerfile

> **Note**: When you push a new commit, Cloudflare Pages will automatically redeploy. The fix to `_redirects` (adding `!`) ensures SPA routing works on direct navigation.
4. Set environment variables:
   - `DATABASE_URL` — Supabase Postgres URL
   - `SUPABASE_URL` — Supabase project URL
   - `SUPABASE_ANON_KEY` — Supabase anon key
   - `LLM_API_KEY` — OpenRouter API key
   - `LLM_BASE_URL` — `https://openrouter.ai/api/v1`
   - `ANTHROPIC_MODEL` — LLM model identifier (e.g. `poolside/laguna-s-2.1:free`). Change this in `.claude/settings.json` to update the model everywhere.
   - `CORS_ORIGINS` — your Cloudflare Pages frontend URL (e.g. `https://job-application-automation.pages.dev`)

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
└── frontend/public/   # Static assets + Cloudflare config
    ├── _redirects    # SPA routing fallback
    └── _headers      # Security headers
```

## License
MIT