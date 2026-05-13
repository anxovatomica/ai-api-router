# Marketing Copy — AI API Router

## Tweet Thread (5 tweets)

**Tweet 1/5**
I got tired of juggling 5 different LLM API keys.

So I built an AI API Router.

One key. Every provider. Auto-fallback when things break.

Drop-in replacement for OpenAI. Free tier included.

Thread 🧵

**Tweet 2/5**
The problem:
- Groq is fast but rate-limits you
- Together has models Groq doesn't
- Fireworks is cheap but flaky

Managing all 3 = constant context switching and failure handling.

**Tweet 3/5**
The solution:

Point your OpenAI client at the router.

It picks the best provider per request, falls back on 429s, and health-checks every 60 seconds.

Your code doesn't change. Your uptime improves.

**Tweet 4/5**
What's inside:
✅ OpenAI-compatible /v1/chat/completions
✅ 12 models mapped across 3 providers
✅ Streaming support (SSE)
✅ Dark admin dashboard
✅ Usage tracking per API key
✅ Self-hosted on Render (free tier)

**Tweet 5/5**
Built this in a weekend. Open source.

Free for 1,000 requests/day.
$5/mo for 10K + smart cost routing.

Repo: github.com/anxovatomica/ai-api-router

Deploy in 2 minutes. Let me know what you think.

---

## Dev.to Article Draft

**Title:** "I Built an AI API Router Because Rate Limits Broke My App"

**Intro:**
Last Tuesday, Groq 429'd me in production. Again. My users saw errors because I hardcoded one provider. I spent the weekend fixing that permanently.

**What it does:**
AI API Router is a smart proxy. You get one API key from us. We route to Groq, Together, Fireworks — whatever's available and cheapest for your model. When a provider chokes, we try the next one. Your users never know.

**Stack:**
FastAPI, SQLite, httpx. Deploys to Render in one click. No external database. No vendor lock-in.

**Key features:**
- OpenAI-compatible endpoint (change your base URL, done)
- Auto-fallback with 60s health checks
- Cost optimization (route to cheapest provider per model)
- Admin dashboard with usage stats
- Daily rate limits per user tier

**Code example:**
```python
import openai
client = openai.OpenAI(
    base_url="https://your-router.com/v1",
    api_key="your_router_key"
)
# Same code. Better uptime.
```

**Conclusion:**
It's open source. Free tier gets you started. If you're running LLMs in production and managing multiple providers manually, this saves you hours.

Repo + deploy link in comments.

---

## Hacker News Launch Post

**Title:** Show HN: AI API Router — One key, every LLM, auto-fallback

**Body:**
I built this after getting rate-limited by Groq during a product demo. The idea is simple: you get one API key, and the router handles provider selection, failover, and health monitoring.

It's a FastAPI app with SQLite. Deploys to Render. OpenAI-compatible so existing code works with a URL change.

Features:
- Routes across Groq, Together, Fireworks
- Auto-fallback on 429/5xx
- 60s health checks
- Usage dashboard
- Streaming support
- Self-hosted

Would love feedback from anyone running LLMs in production. What's your biggest pain point with multi-provider setups?

Repo: https://github.com/anxovatomica/ai-api-router

---

## Reddit Post (r/selfhosted)

**Title:** [Self-hosted] AI API Router — Route LLM requests across providers with auto-fallback

**Body:**
Built a lightweight FastAPI proxy that sits between your app and LLM providers. One API key, multiple backends, automatic failover.

Why I built it: Got tired of rate limits killing my app. Now if Groq is overloaded, it silently tries Together, then Fireworks.

- SQLite (no external DB)
- Docker + Render deploy
- Admin dashboard
- 12 models mapped

Free self-hosted. $5/mo hosted tier.

github.com/anxovatomica/ai-api-router

---

## Product Hunt Launch Copy

**Tagline:** One API key. Every LLM. Zero downtime.

**Description:**
AI API Router is a smart proxy for LLM APIs. Instead of managing multiple provider keys and handling rate limits yourself, you get one key and we route to the best available provider.

**Key features:**
🔄 Auto-fallback across Groq, Together, Fireworks
⚡ OpenAI-compatible (drop-in replacement)
📊 Usage dashboard and per-key rate limits
🐳 Self-hosted with Docker
💰 Cost optimization (cheapest provider wins)

**Maker comment:**
"I built this after a Groq rate limit killed my product demo. Now I never worry about which provider is up — the router handles it."

**Pricing:**
Free: 1,000 req/day
Pro: $5/mo — 10K req/day + smart routing
Enterprise: Custom
