# AI API Load Balancer - Build Spec
## Overview
A smart proxy/router for AI LLM APIs. Users get ONE API key from us. We route to the best available provider (Groq, Together, Fireworks, etc.) based on cost, speed, and availability. Auto-fallback on rate limits. Monetize per-token fee.

## Core Features (MVP)
1. **Unified API endpoint** — `/v1/chat/completions` (OpenAI-compatible)
2. **Provider backends** — Groq (primary), Together AI, Fireworks AI
3. **Smart routing** — Round-robin + fallback on 429/5xx
4. **User API key management** — SQLite DB, simple auth
5. **Usage tracking** — tokens in/out per user per day
6. **Admin endpoints** — `/admin/usage`, `/admin/providers`
7. **Self-healing** — Auto-disable dead providers, re-enable after health check

## Architecture
```
FastAPI app
├── router.py          # Route incoming requests to best provider
├── providers/
│   ├── groq.py        # Groq API wrapper
│   ├── together.py    # Together AI wrapper
│   └── fireworks.py   # Fireworks wrapper
├── db.py              # SQLite: users, usage, provider health
├── auth.py            # API key validation
├── config.py          # Provider credentials from env
└── main.py            # FastAPI app entry
```

## Tech Stack
- Python 3.11 + FastAPI + Uvicorn
- SQLite (no external DB needed)
- httpx (async HTTP)
- python-dotenv
- Render deployment ready

## API Contract (OpenAI-compatible)
```json
POST /v1/chat/completions
Headers: Authorization: Bearer <user_api_key>
Body: {
  "model": "llama-3.1-70b",  // We map to provider-specific model names
  "messages": [...],
  "temperature": 0.7,
  "max_tokens": 1024
}
```

## Deployment
- Render Web Service (free tier first)
- Environment variables for provider API keys
- Auto-deploy on git push

## Monetization
- Free tier: 1000 requests/day
- Pro tier: $5/mo for 10K requests, then $0.50 per 1K
- Enterprise: Custom
- Payment via Stripe (future) — for now, manual via GitHub Sponsors

## File Structure
```
ai-api-router/
├── main.py
├── router.py
├── auth.py
├── db.py
├── config.py
├── requirements.txt
├── Dockerfile
├── render.yaml
├── providers/
│   ├── __init__.py
│   ├── groq.py
│   ├── together.py
│   └── fireworks.py
├── static/
│   └── dashboard.html
└── README.md
```

## MUST HAVES
- Groq MUST work (we have creds)
- OpenAI-compatible response format
- Health checks every 60s
- Request/response logging
- Error handling with fallback
- No manual steps after deploy

## GOD LEVEL REQUIREMENTS
- Single deploy script: `./deploy.sh`
- Auto-provisions on Render
- Auto-creates admin user
- Auto-starts health monitoring
- Self-documenting README with curl examples
