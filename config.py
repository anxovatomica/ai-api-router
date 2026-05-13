import os
from dotenv import load_dotenv

load_dotenv()

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Admin
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-change-me")

# Provider API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "")

# Provider endpoints
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
TOGETHER_BASE_URL = "https://api.together.xyz/v1"
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

# Model mapping (user-facing name → provider-specific)
MODEL_MAP = {
    # Groq models
    "llama-3.1-8b": {"provider": "groq", "model": "llama-3.1-8b-instant"},
    "llama-3.1-70b": {"provider": "groq", "model": "llama-3.1-70b-versatile"},
    "llama-3.1-405b": {"provider": "groq", "model": "llama-3.1-405b-reasoning"},
    "llama-3.3-70b": {"provider": "groq", "model": "llama-3.3-70b-versatile"},
    "mixtral-8x7b": {"provider": "groq", "model": "mixtral-8x7b-32768"},
    "gemma2-9b": {"provider": "groq", "model": "gemma2-9b-it"},
    "deepseek-r1-distill": {"provider": "groq", "model": "deepseek-r1-distill-llama-70b"},
    # Together AI models
    "llama-3-8b-together": {"provider": "together", "model": "meta-llama/Llama-3-8b-chat-hf"},
    "llama-3-70b-together": {"provider": "together", "model": "meta-llama/Llama-3-70b-chat-hf"},
    "mixtral-together": {"provider": "together", "model": "mistralai/Mixtral-8x7B-Instruct-v0.1"},
    # Fireworks models
    "llama-3-8b-fireworks": {"provider": "fireworks", "model": "accounts/fireworks/models/llama-v3p1-8b-instruct"},
    "llama-3-70b-fireworks": {"provider": "fireworks", "model": "accounts/fireworks/models/llama-v3p1-70b-instruct"},
}

# Default model fallback order (if user doesn't specify or model not found)
DEFAULT_PROVIDER_ORDER = ["groq", "together", "fireworks"]

# Health check config
HEALTH_CHECK_INTERVAL_SECONDS = 60
HEALTH_CHECK_TIMEOUT_SECONDS = 10

# Rate limits (requests per minute per provider — soft limits for routing)
PROVIDER_RATE_LIMITS = {
    "groq": 30,
    "together": 20,
    "fireworks": 20,
}

# Pricing: $ per 1M tokens (input + output averaged, rough)
PROVIDER_COST_PER_1M = {
    "groq": 0.59,
    "together": 0.90,
    "fireworks": 0.70,
}