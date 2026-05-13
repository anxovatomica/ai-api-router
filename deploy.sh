#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════
# AI API Router — One-Click Deploy to Render
# ═══════════════════════════════════════════════════════════════

REPO_NAME="ai-api-router"
RENDER_SERVICE_NAME="ai-api-router"

echo "🔥 AI API Router — Deploy Script"
echo "═════════════════════════════════"

# Check prerequisites
if ! command -v git &> /dev/null; then
    echo "❌ git is required. Install it first."
    exit 1
fi

# Optional: check render CLI
if command -v render &> /dev/null; then
    echo "✅ Render CLI detected"
    HAS_RENDER_CLI=true
else
    echo "⚠️  Render CLI not found. Will use manual deploy via git push."
    HAS_RENDER_CLI=false
fi

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "render.yaml" ]; then
    echo "❌ Run this script from the ai-api-router directory (where main.py and render.yaml live)"
    exit 1
fi

# Check for API keys
MISSING_KEYS=""
if [ -z "$GROQ_API_KEY" ]; then
    MISSING_KEYS="$MISSING_KEYS GROQ_API_KEY"
fi
if [ -z "$TOGETHER_API_KEY" ]; then
    MISSING_KEYS="$MISSING_KEYS TOGETHER_API_KEY"
fi
if [ -z "$FIREWORKS_API_KEY" ]; then
    MISSING_KEYS="$MISSING_KEYS FIREWORKS_API_KEY"
fi

if [ -n "$MISSING_KEYS" ]; then
    echo ""
    echo "⚠️  Warning: Some provider API keys are not set:$MISSING_KEYS"
    echo "   The router will run in test mode (mock responses)."
    echo "   Set these before deploying for real LLM access:"
    echo "     export GROQ_API_KEY=your_key"
    echo "     export TOGETHER_API_KEY=your_key"
    echo "     export FIREWORKS_API_KEY=your_key"
    echo ""
fi

# Set admin key if not set
if [ -z "$ADMIN_API_KEY" ]; then
    ADMIN_API_KEY=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")
    echo "🔑 Generated ADMIN_API_KEY: $ADMIN_API_KEY"
    echo "   Save this! You'll need it for admin endpoints."
    echo ""
fi

# Git init if needed
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repo..."
    git init
    git branch -M main
fi

# Commit everything
echo "📤 Committing code..."
git add -A
git commit -m "Deploy AI API Router v1.0.0" || true

echo ""
echo "═══════════════════════════════════════════════════"
echo "🚀 Deploy to Render"
echo "═══════════════════════════════════════════════════"
echo ""

if [ "$HAS_RENDER_CLI" = true ]; then
    echo "Using Render CLI..."
    render deploy || {
        echo "❌ Render CLI deploy failed. Trying manual..."
        HAS_RENDER_CLI=false
    }
fi

if [ "$HAS_RENDER_CLI" = false ]; then
    echo "📋 Manual deploy steps:"
    echo ""
    echo "1. Push this repo to GitHub (or GitLab):"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
    echo "   git push -u origin main"
    echo ""
    echo "2. Go to https://dashboard.render.com/"
    echo "   → Click 'New +' → 'Web Service'"
    echo "   → Connect your GitHub repo"
    echo "   → Render will auto-detect render.yaml and configure everything"
    echo ""
    echo "3. Set environment variables in Render dashboard:"
    echo "   GROQ_API_KEY     = your_groq_key"
    echo "   TOGETHER_API_KEY = your_together_key"
    echo "   FIREWORKS_API_KEY= your_fireworks_key"
    echo "   ADMIN_API_KEY    = $ADMIN_API_KEY"
    echo ""
    echo "4. Deploy! 🎉"
    echo ""
fi

echo "═══════════════════════════════════════════════════"
echo "✅ Deploy script complete!"
echo ""
echo "📖 Quick test after deploy:"
echo "   curl https://YOUR_SERVICE.onrender.com/health"
echo ""
echo "🔑 Admin endpoints:"
echo "   curl -H 'Authorization: Bearer $ADMIN_API_KEY' \\"
echo "        https://YOUR_SERVICE.onrender.com/admin/dashboard"
echo ""
echo "💬 Chat completions:"
echo "   curl -X POST https://YOUR_SERVICE.onrender.com/v1/chat/completions \\"
echo "        -H 'Authorization: Bearer YOUR_USER_API_KEY' \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"model\":\"llama-3.1-70b\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}]}'"
echo ""
echo "═══════════════════════════════════════════════════"
