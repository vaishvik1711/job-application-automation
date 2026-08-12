#!/bin/bash
# =============================================================================
# Railway Deployment Setup Script for Job Automation Backend
# =============================================================================
# Prerequisites:
#   1. You have ALREADY created a Supabase project and collected:
#      - SUPABASE_URL (e.g. https://abcde12345.supabase.co)
#      - SUPABASE_ANON_KEY (starts with eyJ...)
#      - DATABASE_URL (Supabase connection string)
#   2. You have your Vercel frontend URL
#
# Run from the project root: cd "/Users/vaishvik/Desktop/Job Application" && bash backend/setup-railway.sh
# =============================================================================

set -e

echo "🚂 Job Automation Backend — Railway Setup"
echo "=========================================="
echo ""

# --- Load .env file if env vars not already set ------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

if [ ! -z "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
    echo "📄 Loading credentials from $ENV_FILE"
    # Source only the variables we need (safe .env parsing)
    set -a
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        # Remove any surrounding whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        # Export if not already set
        if [ -n "$key" ]; then
            export "$key=$value" 2>/dev/null || true
        fi
    done < "$ENV_FILE"
    set +a
    echo "✅ Credentials loaded from .env"
    echo ""
fi

# --- Check prerequisites -----------------------------------------------------
echo "📋 Prerequisites Check"
echo "   - Supabase URL: ${SUPABASE_URL:+✅ provided}"
echo "   - Supabase Anon Key: ${SUPABASE_ANON_KEY:+✅ provided}"
echo "   - Supabase Database URL: ${DATABASE_URL:+✅ provided}"
echo "   - Vercel Frontend URL: ${VERCEL_FRONTEND_URL:+✅ provided}"
echo ""

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_ANON_KEY" ] || [ -z "$DATABASE_URL" ]; then
    echo "⚠️  Missing Supabase credentials."
    echo "    1. Add them to backend/.env"
    echo "    2. Or pass them as environment variables:"
    echo ""
    echo "    SUPABASE_URL='https://your-project.supabase.co' \\"
    echo "    SUPABASE_ANON_KEY='your-anon-key' \\"
    echo "    DATABASE_URL='postgresql://postgres:pass@host:5432/postgres' \\"
    echo "    bash backend/setup-railway.sh"
    echo ""
    echo "    See DEPLOYMENT.md for full instructions."
    exit 1
fi

# Default Vercel URL — use VERCEL_FRONTEND_URL if provided, otherwise use CORS_ORIGINS from .env
VERCEL_FRONTEND_URL="${VERCEL_FRONTEND_URL:-${CORS_ORIGINS:-https://frontend-taupe-xi-66.vercel.app}}"

# --- Install Railway CLI if needed -------------------------------------------
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
    echo "✅ Railway CLI installed"
fi

# --- Login ---------------------------------------------------------------
if ! railway whoami &> /dev/null; then
    echo "🔑 Logging in to Railway..."
    railway login
fi

# --- Initialize project --------------------------------------------------
echo ""
echo "📦 Initializing Railway project..."
railway init --name job-automation-backend

# --- Set environment variables -------------------------------------------
echo ""
echo "🔧 Setting environment variables..."

railway env set LLM_API_KEY="$LLM_API_KEY"
railway env set LLM_BASE_URL="https://openrouter.ai/api/v1"
railway env set ANTHROPIC_MODEL="poolside/laguna-s-2.1:free"
railway env set SUPABASE_URL="$SUPABASE_URL"
railway env set SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"
railway env set DATABASE_URL="$DATABASE_URL"
railway env set CORS_ORIGINS="$VERCEL_FRONTEND_URL"
railway env set LOG_LEVEL="INFO"
railway env set HEADLESS="false"
railway env set AUTO_SUBMIT="false"

echo "✅ All environment variables set"

# --- Deploy ----------------------------------------------------------------
echo ""
echo "🚀 Deploying to Railway..."
railway up

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔗 Your backend URL will be shown above (ends in .up.railway.app)"
echo "   Save it — you'll need it for Vercel environment variables."
echo ""
echo "📝 Next steps:"
echo "   1. Copy the Railway URL"
echo "   2. Go to your Vercel project → Settings → Environment Variables"
echo "   3. Add: VITE_API_URL = <your-railway-url>"
echo "   4. Add: VITE_SUPABASE_URL = $SUPABASE_URL"
echo "   5. Add: VITE_SUPABASE_ANON_KEY = $SUPABASE_ANON_KEY"
echo "   6. Redeploy Vercel:  vercel --prod"
