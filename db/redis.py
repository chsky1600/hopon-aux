import redis
import os

redis_url = os.getenv('REDIS_URL')
redis_client = redis.from_url(redis_url)

def test_connection():
    try:
        redis_client.ping()
        return "Redis connection successful!"
    except redis.ConnectionError as e:
        return f"Redis connection failed: {e}"