from fastapi import HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import db as db_module

security = HTTPBearer(auto_error=False)

async def validate_api_key(authorization: str = Header(None)) -> dict:
    """Validate user API key from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Support "Bearer <key>" or just "<key>"
    if authorization.lower().startswith("bearer "):
        api_key = authorization[7:].strip()
    else:
        api_key = authorization.strip()
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    user = await db_module.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check daily limit
    daily_usage = await db_module.check_daily_usage(api_key)
    daily_limit = user.get("daily_limit", 1000)
    if daily_usage >= daily_limit:
        raise HTTPException(
            status_code=429, 
            detail=f"Daily request limit exceeded ({daily_usage}/{daily_limit}). Upgrade your plan."
        )
    
    return user

async def validate_admin_key(authorization: str = Header(None)) -> bool:
    """Validate admin API key."""
    from config import ADMIN_API_KEY
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if authorization.lower().startswith("bearer "):
        api_key = authorization[7:].strip()
    else:
        api_key = authorization.strip()
    
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    return True

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"air_{secrets.token_urlsafe(32)}"
