# Deployment Guide — Supabase → Railway → Vercel

This guide walks you through making the **AI Job Application Automation System** live, in the correct order: Supabase (database + storage) → Railway (backend) → Vercel (frontend).

---

## Prerequisites

- GitHub account (to connect repos to Railway/Vercel)
- Node.js 18+ installed locally

---

## Step 1: Set Up Supabase (Database + File Storage)

### 1.1 Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in (use your GitHub account)
2. Click **"New project"**
3. Fill in:
   - **Name**: `job-automation`
   - **Password**: (set a strong password for the database)
   - **Region**: `us-east-1 (Virginia, N. Virginia)`
4. Click **"Create new project"** (takes ~2-5 minutes to provision)

### 1.2 Collect Credentials

Once the project is ready, go to **Project Settings → API**:

| What | Where |
|---|---|
| **API URL** (SUPABASE_URL) | https://[your-project].supabase.co |
| **anon/public key** (SUPABASE_ANON_KEY) | Listed under "Project API keys" |
| **Connection string** (DATABASE_URL) | https://[your-project].supabase.co → Settings → Database → Connection string |

> **Note**: The connection string looks like: `postgresql://postgres:[password]@[host].supabase.co:5432/postgres`
> Replace `[password]` with the database password you set in 1.2.

### 1.3 Create Storage Bucket

In the Supabase Studio (left sidebar):
1. Go to **Storage** → **Create bucket**
2. Name it `resumes`
3. Set to **Private** (not public)

### 1.4 Run Migrations (Optional)

If you have SQL migrations in `supabase/migrations/`:
```bash
supabase db push
```
Otherwise, the backend will auto-create tables on startup.

---

## Step 2: Deploy Backend to Railway

### 2.1 Install Railway CLI

```bash
npm install -g @railway/cli
```

### 2.2 Log in to Railway

```bash
railway login
```

### 2.3 Set Environment Variables

```bash
cd "/Users/vaishvik/Desktop/Job Application"
railway init --name job-automation-backend

# Set env vars (using the keys you found in Step 1)
railway env set LLM_API_KEY="sk-or-v1-..."  # Your OpenRouter API key
railway env set LLM_BASE_URL="https://openrouter.ai/api/v1"
railway env set ANTHROPIC_MODEL="poolside/laguna-s-2.1:free"
railway env set SUPABASE_URL="https://[your-project].supabase.co"
railway env set SUPABASE_ANON_KEY="your-supabase-anon-key"
railway env set DATABASE_URL="postgresql://postgres:[password]@[host].supabase.co:5432/postgres"
railway env set CORS_ORIGINS="https://[your-vercel-url].vercel.app"
railway env set LOG_LEVEL="INFO"
```

### 2.4 Deploy

```bash
railway up
```

Railway will:
- Build the Docker image from `backend/api/Dockerfile`
- Run migrations / create tables on startup
- Provide a URL like `https://job-automation-backend-production.up.railway.app`

**Save this URL** — you'll need it for the Vercel setup.

---

## Step 3: Deploy Frontend to Vercel

### 3.1 Install Vercel CLI

```bash
npm install -g vercel
```

### 3.2 Set Environment Variables

```bash
cd "/Users/vaishvik/Desktop/Job Application/frontend"

# Set your environment variables in Vercel
# (Do this in the Vercel dashboard at vercel.com/my-projects → [project] → Settings → Environment Variables)

# Or use the CLI:
vercel link  # Link to your existing project or create new

# Environment Variables to add:
# Variable Name | Value
# VITE_API_URL  | https://[your-railway-url].up.railway.app
# VITE_SUPABASE_URL | https://[your-project].supabase.co
# VITE_SUPABASE_ANON_KEY | your-supabase-anon-key
# VITE_ANTHROPIC_MODEL | poolside/laguna-s-2.1:free
```

### 3.3 Deploy

```bash
cd "/Users/vaishvik/Desktop/Job Application/frontend"
vercel --prod --yes
```

Or deploy via the Vercel dashboard:
1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo
3. Set **Framework Preset**: `Vite`
4. Set **Root Directory**: `frontend`
5. Add all environment variables (from the table above)
6. Click **"Deploy"**

---

## Verification Checklist

| ✅ | Check |
|---|---|
| Supabase | Database created, `resumes` bucket exists, URL + anon key captured |
| Railway | Backend deployed, health check passes (`/health`), URL captured |
| Vercel | Frontend deployed, can access the dashboard, API calls succeed |
| CORS | Frontend URL added to `CORS_ORIGINS` in Railway |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `CORS error` on frontend | Add your Vercel URL to `CORS_ORIGINS` in Railway env vars |
| `Supabase not configured` | Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set in Railway |
| `LLM_API_KEY not configured` | Verify `LLM_API_KEY` is set in Railway (should be your OpenRouter key) |
| Health check fails | Check Railway logs: `railway logs` |
| Build fails | Ensure `backend/api/Dockerfile` and all requirements are intact |

---

## All Environment Variables Summary

### Railway (Backend)
| Variable | Example |
|---|---|
| `DATABASE_URL` | `postgresql://postgres:PASSWORD@db.X.supabase.co:5432/postgres` |
| `LLM_API_KEY` | `sk-or-v1-...` (from OpenRouter) |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` |
| `ANTHROPIC_MODEL` | `poolside/laguna-s-2.1:free` |
| `SUPABASE_URL` | `https://project.supabase.co` |
| `SUPABASE_ANON_KEY` | `eyJ...` (from Supabase) |
| `CORS_ORIGINS` | `https://frontend.vercel.app` |
| `LOG_LEVEL` | `INFO` |

### Vercel (Frontend)
| Variable | Example |
|---|---|
| `VITE_API_URL` | `https://job-automation.up.railway.app` |
| `VITE_SUPABASE_URL` | `https://project.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | `eyJ...` (same as backend) |
| `VITE_ANTHROPIC_MODEL` | `poolside/laguna-s-2.1:free` |
