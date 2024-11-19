from datetime import timedelta, datetime
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

def insert_qr_token(session_id, token, expiration=timedelta(minutes=30)):
    """
    Insert a QR token into the session's Redis sorted set and set expiration.

    :param session_id: The ID of the session.
    :param token: The QR token to be added.
    :param expiration: Expiration time for the session set.
    """
    session_set_name = f"session_{session_id}"
    expiration_timestamp = (datetime.now() + expiration).timestamp()

    # Add the token to the sorted set with its expiration timestamp as the score
    redis_client.zadd(session_set_name, {token: expiration_timestamp})
    
    # Set the expiration time for the session set itself
    redis_client.expire(session_set_name, expiration)

def get_valid_token(session_id):
    """
    Retrieve the first valid token (non-expired) from the session set.

    :param session_id: The ID of the session.
    :return: The first valid token or None if no valid token exists.
    """
    session_set_name = f"session_{session_id}"
    current_time = datetime.now().timestamp()

    # Get the first token whose expiration time has not passed
    tokens = redis_client.zrangebyscore(session_set_name, current_time, '+inf', start=0, num=1)
    
    if tokens:
        return tokens[0].decode('utf-8')
    return None

def remove_expired_tokens(session_id):
    """
    Remove expired tokens from the session set.

    :param session_id: The ID of the session.
    """
    session_set_name = f"session_{session_id}"
    current_time = datetime.now().timestamp()

    # Remove tokens that are expired
    redis_client.zremrangebyscore(session_set_name, '-inf', current_time)

def delete_session_set(session_id):
    session_set_name = f"session_{session_id}"
    tokens = redis_client.zrange(session_set_name, 0, -1)
    
    print(f"Deleting session set: {session_set_name} with tokens: {tokens}")  # Debug

    for token in tokens:
        redis_client.delete(f"qr_token:{token.decode('utf-8')}")
        print(f"Deleted token: {token.decode('utf-8')}")  # Debug
    
    redis_client.delete(session_set_name)
    print(f"Deleted session set: {session_set_name}")  # Debug