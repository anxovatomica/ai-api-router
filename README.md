# AI API Router 🔥

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/anxovatomica/ai-api-router)

**Smart proxy/router for AI LLM APIs.** One API key, multiple providers (Groq, Together AI, Fireworks), auto-fallback on failures.

**🌐 Live Demo:** http://43.98.167.138:8001

## What It Does

- **One API key** → routes to the best available LLM provider
- **Auto-fallback** when a provider hits rate limits (429) or errors (5xx)
- **Health checks** every 60 seconds — dead providers auto-disable, healthy ones auto-re-enable
- **Usage tracking** — tokens in/out per user per day, stored in SQLite
- **OpenAI-compatible** `/v1/chat/completions` endpoint
- **Admin dashboard** — stats, users, provider health

## Quick Start

### 1. Clone & Install

```bash
git clone <your-repo>
cd ai-api-router
pip install -r requirements.txt
```

### 2. Set Env Vars

```bash
export GROQ_API_KEY="your_groq_key"
export TOGETHER_API_KEY="your_together_key"
export FIREWORKS_API_KEY="your_fireworks_key"
export ADMIN_API_KEY="admin-secret-change-me"
```

### 3. Run

```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000
```

The app auto-creates the first user on startup and prints the API key.

---

## API Usage

### Chat Completions (OpenAI-compatible)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_USER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-70b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

### Streaming

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_USER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-70b",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```

### List Models

```bash
curl http://localhost:8000/v1/models
```

### Health Check

```bash
curl http://localhost:8000/health
```

---

## Admin Endpoints

All admin endpoints require `Authorization: Bearer ADMIN_API_KEY`.

### Dashboard (overview)

```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/admin/dashboard
```

### Usage Stats

```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/admin/usage?days=7
```

### List Users

```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/admin/users
```

### Create User

```bash
curl -X POST http://localhost:8000/admin/users \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com", "tier": "pro"}'
```

### Provider Status

```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/admin/providers
```

### Reset Provider (mark healthy)

```bash
curl -X POST http://localhost:8000/admin/providers/groq/reset \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

### Per-User Usage

```bash
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/admin/user/USER_API_KEY/usage?days=7
```

---

## Available Models

| User-facing name | Provider | Actual model |
|---|---|---|
| `llama-3.1-8b` | Groq | `llama-3.1-8b-instant` |
| `llama-3.1-70b` | Groq | `llama-3.1-70b-versatile` |
| `llama-3.1-405b` | Groq | `llama-3.1-405b-reasoning` |
| `llama-3.3-70b` | Groq | `llama-3.3-70b-versatile` |
| `mixtral-8x7b` | Groq | `mixtral-8x7b-32768` |
| `gemma2-9b` | Groq | `gemma2-9b-it` |
| `deepseek-r1-distill` | Groq | `deepseek-r1-distill-llama-70b` |
| `llama-3-8b-together` | Together | `meta-llama/Llama-3-8b-chat-hf` |
| `llama-3-70b-together` | Together | `meta-llama/Llama-3-70b-chat-hf` |
| `mixtral-together` | Together | `mistralai/Mixtral-8x7B-Instruct-v0.1` |
| `llama-3-8b-fireworks` | Fireworks | `accounts/fireworks/models/llama-v3p1-8b-instruct` |
| `llama-3-70b-fireworks` | Fireworks | `accounts/fireworks/models/llama-v3p1-70b-instruct` |

---

## Deploy to Render

### Option A: One-Click Deploy Script

```bash
export GROQ_API_KEY="your_key"
./deploy.sh
```

The script will:
1. Check for API keys
2. Generate an admin key
3. Commit code
4. Walk you through Render deploy

### Option B: Manual Deploy

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click **New +** → **Web Service**
4. Connect your GitHub repo
5. Render auto-detects `render.yaml`
6. Set environment variables:
   - `GROQ_API_KEY`
   - `TOGETHER_API_KEY`
   - `FIREWORKS_API_KEY`
   - `ADMIN_API_KEY`
7. Deploy!

---

## Architecture

```
User Request
    → Auth (API key validation + daily limit check)
    → Router (resolve model → pick best provider)
    → Provider (Groq / Together / Fireworks)
    → Fallback (on 429/5xx, try next provider)
    → Log (tokens, latency, status to SQLite)
    → Response (OpenAI-compatible JSON)
```

Background task: health checks every 60s.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | No | — | Groq API key |
| `TOGETHER_API_KEY` | No | — | Together AI key |
| `FIREWORKS_API_KEY` | No | — | Fireworks key |
| `ADMIN_API_KEY` | No | `admin-secret-change-me` | Admin access key |
| `PORT` | No | `8000` | Server port |
| `HOST` | No | `0.0.0.0` | Bind host |
| `DEBUG` | No | `false` | Debug mode |
| `DB_PATH` | No | `ai_router.db` | SQLite file path |

---

## Docker

```bash
docker build -t ai-api-router .
docker run -p 8000:8000 -e GROQ_API_KEY=xxx ai-api-router
```

---

## License

MIT
