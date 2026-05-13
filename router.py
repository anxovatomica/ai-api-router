import time
from typing import Dict, Any, Optional
from fastapi import HTTPException

from providers import GroqProvider, TogetherProvider, FireworksProvider
import db as db_module
from config import (
    MODEL_MAP, DEFAULT_PROVIDER_ORDER, DEBUG,
    HEALTH_CHECK_INTERVAL_SECONDS
)

class ProviderRouter:
    def __init__(self):
        self.providers = {
            "groq": GroqProvider(),
            "together": TogetherProvider(),
            "fireworks": FireworksProvider(),
        }
        self._provider_index = 0  # round-robin counter
        self._health_check_running = False
    
    def resolve_model(self, model_name: str) -> Dict[str, str]:
        """Map user-facing model name to provider-specific model name."""
        if model_name in MODEL_MAP:
            return MODEL_MAP[model_name]
        
        # Try to find a partial match
        for key, mapped in MODEL_MAP.items():
            if key in model_name or model_name in key:
                return mapped
        
        # Default: assume it's a direct model name, try Groq first
        return {"provider": "groq", "model": model_name}
    
    async def get_best_provider(self, preferred: Optional[str] = None) -> tuple[str, Any]:
        """Get the best available provider using round-robin + health."""
        health = await db_module.get_all_provider_health()
        health_map = {h["provider"]: h for h in health}
        
        candidates = []
        
        # If a specific provider is preferred, try that first
        if preferred and preferred in self.providers:
            candidates = [preferred] + [p for p in DEFAULT_PROVIDER_ORDER if p != preferred]
        else:
            candidates = list(DEFAULT_PROVIDER_ORDER)
        
        # Filter to healthy providers
        healthy = []
        for name in candidates:
            h = health_map.get(name, {})
            if h.get("is_healthy", 1) == 1:
                healthy.append(name)
        
        if not healthy:
            # All providers down — still try, but warn
            if DEBUG:
                print("[Router] WARNING: All providers marked unhealthy, trying anyway")
            healthy = candidates
        
        # Round-robin selection
        provider_name = healthy[self._provider_index % len(healthy)]
        self._provider_index += 1
        
        return provider_name, self.providers[provider_name]
    
    async def route_chat_completion(self, request_body: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Route a chat completion request with auto-fallback."""
        model_name = request_body.get("model", "llama-3.1-70b")
        mapped = self.resolve_model(model_name)
        provider_name = mapped["provider"]
        actual_model = mapped["model"]
        
        # Update request body with actual model name
        body = dict(request_body)
        body["model"] = actual_model
        
        errors = []
        attempted = []
        
        # Try preferred provider first
        for attempt in range(3):
            try:
                chosen_name, provider = await self.get_best_provider(
                    preferred=provider_name if attempt == 0 else None
                )
                
                if chosen_name in attempted:
                    continue
                attempted.append(chosen_name)
                
                start = time.time()
                response = await provider.chat_completions(body)
                latency_ms = int((time.time() - start) * 1000)
                
                # Log success
                usage = response.get("usage", {})
                await db_module.log_usage(
                    api_key=api_key,
                    provider=chosen_name,
                    model=actual_model,
                    tokens_input=usage.get("prompt_tokens", 0),
                    tokens_output=usage.get("completion_tokens", 0),
                    latency_ms=latency_ms,
                    status_code=200
                )
                
                # Mark provider healthy
                await db_module.update_provider_health(chosen_name, True, latency_ms, success=True)
                
                # Update response model name to match user request
                response["model"] = model_name
                
                return response
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{chosen_name}: {error_msg}")
                
                # Check if it's a rate limit or server error — mark unhealthy briefly
                if "429" in error_msg or "500" in error_msg or "502" in error_msg or "503" in error_msg:
                    await db_module.update_provider_health(
                        chosen_name, False, error=error_msg, success=False
                    )
                
                if DEBUG:
                    print(f"[Router] Provider {chosen_name} failed: {error_msg}")
                
                # Try next provider
                continue
        
        # All providers failed
        raise HTTPException(
            status_code=503,
            detail=f"All providers failed. Errors: {' | '.join(errors)}"
        )
    
    async def route_streaming_completion(self, request_body: Dict[str, Any], api_key: str):
        """Route a streaming chat completion request with auto-fallback."""
        model_name = request_body.get("model", "llama-3.1-70b")
        mapped = self.resolve_model(model_name)
        provider_name = mapped["provider"]
        actual_model = mapped["model"]
        
        body = dict(request_body)
        body["model"] = actual_model
        body["stream"] = True
        
        errors = []
        attempted = []
        
        for attempt in range(3):
            try:
                chosen_name, provider = await self.get_best_provider(
                    preferred=provider_name if attempt == 0 else None
                )
                
                if chosen_name in attempted:
                    continue
                attempted.append(chosen_name)
                
                start = time.time()
                
                # Log usage after stream completes (we'll estimate)
                await db_module.log_usage(
                    api_key=api_key,
                    provider=chosen_name,
                    model=actual_model,
                    latency_ms=int((time.time() - start) * 1000),
                    status_code=200
                )
                
                await db_module.update_provider_health(chosen_name, True, success=True)
                
                async for chunk in provider.stream_chat_completions(body):
                    yield chunk
                
                return
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{chosen_name}: {error_msg}")
                
                if "429" in error_msg or "500" in error_msg or "502" in error_msg or "503" in error_msg:
                    await db_module.update_provider_health(
                        chosen_name, False, error=error_msg, success=False
                    )
                
                continue
        
        raise HTTPException(
            status_code=503,
            detail=f"All providers failed. Errors: {' | '.join(errors)}"
        )
    
    async def run_health_checks(self):
        """Run health checks for all providers."""
        if self._health_check_running:
            return
        
        self._health_check_running = True
        try:
            for name, provider in self.providers.items():
                try:
                    healthy, latency, error = await provider.health_check()
                    await db_module.update_provider_health(
                        name, healthy, latency, error=error, success=healthy
                    )
                    if DEBUG:
                        status = "✅" if healthy else "❌"
                        print(f"[Health] {name} {status} ({latency}ms)")
                except Exception as e:
                    await db_module.update_provider_health(
                        name, False, error=str(e), success=False
                    )
                    if DEBUG:
                        print(f"[Health] {name} ❌ ERROR: {e}")
        finally:
            self._health_check_running = False
    
    async def get_provider_status(self) -> list:
        """Get current status of all providers."""
        health = await db_module.get_all_provider_health()
        result = []
        for h in health:
            result.append({
                "provider": h["provider"],
                "is_healthy": bool(h["is_healthy"]),
                "avg_latency_ms": h.get("avg_latency_ms", 0),
                "failure_count": h.get("failure_count", 0),
                "success_count": h.get("success_count", 0),
                "last_error": h.get("last_error"),
                "last_check": h.get("last_check"),
            })
        return result

# Global router instance
router = ProviderRouter()