from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import time
import json

import db as db_module
from auth import validate_api_key, validate_admin_key, generate_api_key
from router import router as provider_router
from config import (
    DEBUG, HOST, PORT, ADMIN_API_KEY,
    HEALTH_CHECK_INTERVAL_SECONDS
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan — init DB and start health check loop."""
    # Startup
    await db_module.init_db()
    
    # Auto-create admin user if none exists
    users = await db_module.list_users()
    if not users:
        admin_key = generate_api_key()
        await db_module.create_user(
            api_key=admin_key,
            name="Admin",
            email="admin@ai-router.local",
            tier="pro"
        )
        if DEBUG:
            print(f"[Startup] Created first user with API key: {admin_key}")
    
    # Initial health check
    await provider_router.run_health_checks()
    
    # Start background health check loop
    health_task = asyncio.create_task(_health_check_loop())
    
    yield
    
    # Shutdown
    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass

async def _health_check_loop():
    """Run health checks every 60 seconds."""
    while True:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
        try:
            await provider_router.run_health_checks()
        except Exception as e:
            if DEBUG:
                print(f"[Health Loop] Error: {e}")

app = FastAPI(
    title="AI API Router",
    description="Smart proxy/router for AI LLM APIs. Route to the best provider with auto-fallback.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── Public endpoints ───

@app.get("/")
async def root():
    return {
        "name": "AI API Router",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/landing", response_class=HTMLResponse)
async def landing_page():
    """Serve the marketing landing page."""
    with open("templates/index.html", "r") as f:
        return f.read()

@app.post("/track-visit")
async def track_visit(request: Request):
    """Track a visit to the landing page."""
    try:
        await db_module.log_visit(
            ip=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
            path="/landing"
        )
    except Exception:
        pass
    return {"status": "ok"}

@app.get("/stats")
async def public_stats():
    """Public stats endpoint for social proof."""
    try:
        users = await db_module.list_users()
        usage_stats = await db_module.get_usage_stats(30)
        total_requests = sum(s.get("requests", 0) for s in usage_stats)
        return {
            "users": len(users),
            "requests_30d": total_requests,
            "providers": 3,
            "models": 12,
            "status": "live"
        }
    except Exception:
        return {"users": 0, "requests_30d": 0, "providers": 3, "models": 12, "status": "live"}

@app.get("/health")
async def health():
    providers = await provider_router.get_provider_status()
    healthy_count = sum(1 for p in providers if p["is_healthy"])
    
    return {
        "status": "healthy" if healthy_count > 0 else "degraded",
        "providers": providers,
        "healthy_count": healthy_count,
        "total_providers": len(providers)
    }

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    from config import MODEL_MAP
    models = []
    for id, mapped in MODEL_MAP.items():
        models.append({
            "id": id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": mapped["provider"],
        })
    return {"object": "list", "data": models}

# ─── Chat completions (OpenAI-compatible) ───

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint."""
    # Extract API key
    authorization = request.headers.get("authorization", "")
    user = await validate_api_key(authorization)
    
    body = await request.json()
    is_streaming = body.get("stream", False)
    
    if is_streaming:
        return StreamingResponse(
            _stream_response(body, user["api_key"]),
            media_type="text/event-stream"
        )
    
    response = await provider_router.route_chat_completion(body, user["api_key"])
    return JSONResponse(content=response)

async def _stream_response(request_body: dict, api_key: str):
    """Generator for streaming responses."""
    try:
        async for chunk in provider_router.route_streaming_completion(request_body, api_key):
            yield chunk
    except HTTPException:
        raise
    except Exception as e:
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "router_error",
                "code": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"

# ─── Admin endpoints ───

@app.get("/admin/usage")
async def admin_usage(days: int = 7, _admin: bool = Header(None)):
    await validate_admin_key(_admin)
    stats = await db_module.get_usage_stats(days)
    return {
        "period_days": days,
        "stats": stats,
        "summary": _summarize_usage(stats)
    }

@app.get("/admin/users")
async def admin_users(_admin: bool = Header(None)):
    await validate_admin_key(_admin)
    users = await db_module.list_users()
    return {"users": users, "count": len(users)}

@app.post("/admin/users")
async def admin_create_user(request: Request, _admin: bool = Header(None)):
    await validate_admin_key(_admin)
    body = await request.json()
    
    api_key = body.get("api_key") or generate_api_key()
    user = await db_module.create_user(
        api_key=api_key,
        name=body.get("name"),
        email=body.get("email"),
        tier=body.get("tier", "free")
    )
    return user

@app.get("/admin/providers")
async def admin_providers(_admin: bool = Header(None)):
    await validate_admin_key(_admin)
    return {
        "providers": await provider_router.get_provider_status(),
        "model_map": {k: v for k, v in __import__("config").MODEL_MAP.items()}
    }

@app.post("/admin/providers/{provider}/reset")
async def admin_reset_provider(provider: str, _admin: bool = Header(None)):
    await validate_admin_key(_admin)
    await db_module.reset_provider_health(provider)
    return {"status": "reset", "provider": provider}

@app.get("/admin/user/{api_key}/usage")
async def admin_user_usage(api_key: str, days: int = 7, _admin: bool = Header(None)):
    await validate_admin_key(_admin)
    return {
        "api_key": api_key,
        "days": days,
        "usage": await db_module.get_user_usage(api_key, days)
    }

@app.get("/admin/dashboard")
async def admin_dashboard(_admin: bool = Header(None)):
    await validate_admin_key(_admin)
    
    # Gather all stats
    usage_stats = await db_module.get_usage_stats(7)
    provider_stats = await db_module.get_provider_stats()
    users = await db_module.list_users()
    providers = await provider_router.get_provider_status()
    
    return {
        "summary": {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.get("is_active")),
            "total_requests_7d": sum(s.get("requests", 0) for s in usage_stats),
            "total_tokens_7d": sum(s.get("tokens_total", 0) for s in usage_stats),
            "healthy_providers": sum(1 for p in providers if p["is_healthy"]),
            "total_providers": len(providers),
        },
        "provider_stats": provider_stats,
        "providers": providers,
        "usage_by_day": usage_stats,
        "users": users
    }

# ─── Dashboard ───

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the admin dashboard HTML."""
    with open("static/dashboard.html", "r") as f:
        return f.read()

# ─── Helper functions ───

def _summarize_usage(stats: list) -> dict:
    if not stats:
        return {"total_requests": 0, "total_tokens": 0, "avg_latency": 0}
    
    total_requests = sum(s.get("requests", 0) for s in stats)
    total_tokens = sum(s.get("tokens_total", 0) for s in stats)
    avg_latency = sum(s.get("avg_latency", 0) for s in stats) / len(stats) if stats else 0
    
    return {
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "avg_latency_ms": round(avg_latency, 2)
    }

# ─── Run ───

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)
