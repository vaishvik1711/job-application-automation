# AI Job Application Automation System

A full-stack AI-powered job application automation system with a React frontend dashboard and FastAPI backend.

## Architecture

- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
- **Backend**: Python FastAPI with async SQLAlchemy
- **Database**: Supabase Postgres
- **File Storage**: Supabase Storage
- **LLM**: OpenRouter (poolside/laguna-s-2.1:free)
- **Deployment**: Vercel (frontend) + Render.com (backend)

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

### Backend Deployment (Render.com)
1. Create a new Web Service on [render.com](https://render.com)
2. Connect your GitHub repo
3. Set build command: `pip install -r backend/requirements.txt -r backend/api/requirements.txt`
4. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Set environment variables:
   - `DATABASE_URL` — Supabase Postgres URL
   - `SUPABASE_URL` — Supabase project URL
   - `SUPABASE_ANON_KEY` — Supabase anon key
   - `LLM_API_KEY` — OpenRouter API key
   - `LLM_BASE_URL` — `https://openrouter.ai/api/v1`
   - `LLM_MODEL` — `poolside/laguna-s-2.1:free`
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