import aiosqlite
import json
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any

DB_PATH = os.getenv("DB_PATH", "ai_router.db")

async def init_db():
    """Initialize SQLite database with all tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT UNIQUE NOT NULL,
                name TEXT,
                email TEXT,
                tier TEXT DEFAULT 'free',
                daily_limit INTEGER DEFAULT 1000,
                monthly_limit INTEGER DEFAULT 10000,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Usage tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                tokens_total INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                status_code INTEGER DEFAULT 200,
                error TEXT,
                day TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Provider health
        await db.execute("""
            CREATE TABLE IF NOT EXISTS provider_health (
                provider TEXT PRIMARY KEY,
                is_healthy INTEGER DEFAULT 1,
                last_check TEXT,
                avg_latency_ms INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Visit tracking for landing page
        await db.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                user_agent TEXT,
                path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize provider health rows
        for provider in ["groq", "together", "fireworks"]:
            await db.execute("""
                INSERT OR IGNORE INTO provider_health (provider, is_healthy, last_check)
                VALUES (?, 1, ?)
            """, (provider, datetime.utcnow().isoformat()))
        
        await db.commit()

async def get_db():
    """Get database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

# ─── User operations ───

async def create_user(api_key: str, name: str = None, email: str = None, tier: str = "free") -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (api_key, name, email, tier) VALUES (?, ?, ?, ?)",
            (api_key, name, email, tier)
        )
        await db.commit()
        return {"api_key": api_key, "name": name, "email": email, "tier": tier}

async def get_user_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def list_users() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def check_daily_usage(api_key: str) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) as count FROM usage WHERE api_key = ? AND day = ?",
            (api_key, today)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# ─── Usage operations ───

async def log_usage(
    api_key: str,
    provider: str,
    model: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    latency_ms: int = 0,
    status_code: int = 200,
    error: str = None
) -> None:
    today = date.today().isoformat()
    tokens_total = tokens_input + tokens_output
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO usage 
            (api_key, provider, model, tokens_input, tokens_output, tokens_total, latency_ms, status_code, error, day)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (api_key, provider, model, tokens_input, tokens_output, tokens_total, latency_ms, status_code, error, today))
        await db.commit()

async def get_usage_stats(days: int = 7) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                day,
                provider,
                COUNT(*) as requests,
                SUM(tokens_input) as tokens_input,
                SUM(tokens_output) as tokens_output,
                SUM(tokens_total) as tokens_total,
                AVG(latency_ms) as avg_latency
            FROM usage
            WHERE day >= date('now', '-{} days')
            GROUP BY day, provider
            ORDER BY day DESC, provider
        """.format(days)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_usage(api_key: str, days: int = 7) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                day,
                provider,
                COUNT(*) as requests,
                SUM(tokens_input) as tokens_input,
                SUM(tokens_output) as tokens_output,
                SUM(tokens_total) as tokens_total
            FROM usage
            WHERE api_key = ? AND day >= date('now', '-{} days')
            GROUP BY day, provider
            ORDER BY day DESC
        """.format(days), (api_key,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_provider_stats() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                provider,
                COUNT(*) as total_requests,
                SUM(tokens_total) as total_tokens,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
            FROM usage
            GROUP BY provider
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# ─── Provider health operations ───

async def get_provider_health(provider: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM provider_health WHERE provider = ?", (provider,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def get_all_provider_health() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM provider_health") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_provider_health(
    provider: str,
    is_healthy: bool,
    latency_ms: int = 0,
    error: str = None,
    success: bool = True
) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if success:
            await db.execute("""
                UPDATE provider_health 
                SET is_healthy = ?, last_check = ?, avg_latency_ms = ?, 
                    success_count = success_count + 1, updated_at = ?
                WHERE provider = ?
            """, (1 if is_healthy else 0, now, latency_ms, now, provider))
        else:
            await db.execute("""
                UPDATE provider_health 
                SET is_healthy = ?, last_check = ?, failure_count = failure_count + 1,
                    last_error = ?, updated_at = ?
                WHERE provider = ?
            """, (1 if is_healthy else 0, now, error, now, provider))
        await db.commit()

async def reset_provider_health(provider: str) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE provider_health 
            SET is_healthy = 1, last_check = ?, failure_count = 0, last_error = NULL, updated_at = ?
            WHERE provider = ?
        """, (now, now, provider))
        await db.commit()

# ─── Visit tracking ───

async def log_visit(ip: str, user_agent: str, path: str) -> None:
    """Log a visit to the landing page."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO visits (ip, user_agent, path) VALUES (?, ?, ?)",
            (ip, user_agent, path)
        )
        await db.commit()

async def get_visit_count(days: int = 30) -> int:
    """Get total visit count for the last N days."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM visits WHERE created_at >= date('now', '-{} days')".format(days)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
