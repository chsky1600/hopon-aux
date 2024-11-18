from datetime import timedelta
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

def test_connection():
    try:
        redis_client.ping()
        return "Redis connection successful!"
    except redis.ConnectionError as e:
        return f"Redis connection failed: {e}"

def insert_qr_token(session_id, token, expiration=timedelta(minutes=30)):
    """
    Insert a QR token into the session's Redis set and set expiration.
    
    :param session_id: The ID of the session.
    :param token: The QR token to be added.
    :param expiration: Expiration time for the session set.
    """
    session_set_name = f"session_{session_id}"
    redis_client.sadd(session_set_name, token)
    redis_client.expire(session_set_name, expiration)
    return f"Token {token} added to {session_set_name} with expiration of {expiration}"

def delete_session_set(session_id):
    """
    Delete the entire session set and its tokens from Redis.

    :param session_id: The ID of the session.
    """
    session_set_name = f"session_{session_id}"
    tokens = redis_client.smembers(session_set_name)
    
    for token in tokens:
        redis_client.delete(token.decode('utf-8'))
    
    redis_client.delete(session_set_name)
    return f"Session set {session_set_name} and associated tokens deleted"