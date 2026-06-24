import os
import json
import logging
from typing import List
import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")

try:
    if REDIS_URL:
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        # Log safely without showing credentials
        safe_url = REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL
        logger.info(f"Successfully connected to Redis using URL: {safe_url}")
    else:
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    
    if redis_client:
        redis_client.ping()
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

def get_user_history(user_id: str) -> List[str]:
    """Retrieve user history list from Redis."""
    if not redis_client:
        logger.warning("Redis client is not initialized.")
        return []
    try:
        data = redis_client.get(f"user:history:{user_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Error reading user history from Redis: {e}")
    return []

def save_user_history(user_id: str, history: List[str]) -> bool:
    """Save user history list to Redis."""
    if not redis_client:
        logger.warning("Redis client is not initialized.")
        return False
    try:
        redis_client.set(f"user:history:{user_id}", json.dumps(history))
        return True
    except Exception as e:
        logger.error(f"Error saving user history to Redis: {e}")
        return False
