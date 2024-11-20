from datetime import timedelta, datetime
import redis
import os
from app import app
import uuid


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
    redis_client.zadd(session_set_name, {f"token:{token}": expiration_timestamp})
    
    print(f"\nAdding token to session ID: {session_id}\n")
    
    # Set the expiration time for the session set itself
    redis_client.expire(session_set_name, expiration)
    
def insert_active_scanner(session_id, scanner, expiration=timedelta(minutes=30)):
    
    session_set_name = f"session_{session_id}"
    expiration_timestamp = (datetime.now() + expiration).timestamp()

    # Add the scanner to the sorted set with a prefix
    redis_client.zadd(session_set_name, {f"scanner:{scanner}": expiration_timestamp})
    
    # Ensure the session set has the correct expiration time
    redis_client.expire(session_set_name, expiration)
    print("Current set contents:", redis_client.zrange(session_set_name, 0, -1, withscores=True))
    

def get_valid_token(session_id):
    """
    Retrieve the first valid token (non-expired) from the session set.

    :param session_id: The ID of the session.
    :return: The first valid token or None if no valid token exists.
    """
    session_set_name = f"session_{session_id}"
    current_time = datetime.now().timestamp()

    # Get the first token whose expiration time has not passed
    members = redis_client.zrangebyscore(session_set_name, current_time, '+inf')

    # Debugging: Log retrieved members
    print(f"Members object: {members}")
    print(f"Members retrieved: {[member.decode('utf-8') for member in members]}")
    
    for member in members:
        member_str = member.decode('utf-8')
        if member_str.startswith('token:'):
            token = member_str.split(":", 1)[1]
            print(f"Valid token found: {token}")
            return token

    # If no valid token is found, generate a new one
    print("No valid token found, generating a new one.")
    token = str(uuid.uuid4())
    insert_qr_token(session_id, token, app.config['TOKEN_EXPIRATION'])
    return token

def remove_expired_members(session_id):
    """
    Remove expired tokens from the session set.

    :param session_id: The ID of the session.
    """
    session_set_name = f"session_{session_id}"
    current_time = datetime.now().timestamp()

    # Remove tokens that are expired
    redis_client.zremrangebyscore(session_set_name, '-inf', current_time)

def delete_session_set(session_id):
    """
    Delete the session's sorted set and its associated tokens and scanners.

    :param session_id: The ID of the session.
    """
    session_set_name = f"session_{session_id}"
    members = redis_client.zrange(session_set_name, 0, -1)

    print(f"Deleting session set: {session_set_name} with members: {members}")  # Debug

    for member in members:
        member_str = member.decode('utf-8')

        if member_str.startswith("token:"):
            token = member_str.split(":", 1)[1]  # Extract the token value
            redis_client.delete(f"qr_token:{token}")  # Clean up token-specific keys if necessary
            print(f"Deleted token: {token}")  # Debug

        elif member_str.startswith("scanner:"):
            scanner = member_str.split(":", 1)[1]  # Extract the scanner name
            print(f"Deleted scanner: {scanner}")  # Debug
            # No additional cleanup needed for scanners unless they have associated keys

    # Delete the entire sorted set
    redis_client.delete(session_set_name)
    print(f"Deleted session set: {session_set_name}")  # Debug
    