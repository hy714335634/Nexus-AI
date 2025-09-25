"""
Redis client configuration
"""
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

import logging
from typing import Optional, Any
import json

from api.core.config import settings
from api.core.exceptions import APIException

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for caching and session management"""
    
    def __init__(self):
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using mock implementation")
            self.redis = None
            return
            
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis = None
            logger.warning("Using mock Redis implementation")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.redis:
            return None
            
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        if not self.redis:
            return True  # Mock success
            
        try:
            serialized_value = json.dumps(value, default=str)
            result = self.redis.set(key, serialized_value, ex=expire)
            return result
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.redis:
            return True  # Mock success
            
        try:
            result = self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis:
            return False  # Mock not exists
            
        try:
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking key {key} in Redis: {str(e)}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in Redis"""
        if not self.redis:
            return amount  # Mock increment
            
        try:
            return self.redis.incr(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing key {key} in Redis: {str(e)}")
            return 0
    
    def set_hash(self, key: str, mapping: dict, expire: Optional[int] = None) -> bool:
        """Set hash in Redis"""
        if not self.redis:
            return True  # Mock success
            
        try:
            # Serialize complex values
            serialized_mapping = {}
            for k, v in mapping.items():
                if isinstance(v, (dict, list)):
                    serialized_mapping[k] = json.dumps(v, default=str)
                else:
                    serialized_mapping[k] = str(v)
            
            result = self.redis.hset(key, mapping=serialized_mapping)
            if expire:
                self.redis.expire(key, expire)
            return result
        except Exception as e:
            logger.error(f"Error setting hash {key} in Redis: {str(e)}")
            return False
    
    def get_hash(self, key: str) -> Optional[dict]:
        """Get hash from Redis"""
        if not self.redis:
            return None  # Mock not found
            
        try:
            result = self.redis.hgetall(key)
            if not result:
                return None
            
            # Deserialize complex values
            deserialized_result = {}
            for k, v in result.items():
                try:
                    deserialized_result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    deserialized_result[k] = v
            
            return deserialized_result
        except Exception as e:
            logger.error(f"Error getting hash {key} from Redis: {str(e)}")
            return None

# Global Redis client instance
try:
    redis_client = RedisClient()
except Exception as e:
    logger.warning(f"Failed to initialize Redis client: {e}")
    redis_client = None