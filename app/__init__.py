# app/__init__.py

from flask import Flask, session
from flask_session import Session
from flask_socketio import SocketIO, join_room, leave_room, emit, disconnect
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import secrets
from datetime import timedelta

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
socketio = SocketIO(app)

@socketio.on('song_request')
def handle_song_request(data):
    session_id = data.get('scanner_id')
    track_uri = data.get('track_uri')

    if not session_id or not track_uri:
        print("Invalid song request data.")
        return

    # Get the host's Spotify client
    sp_host = get_spotify_client()
    if not sp_host:
        print("Host is not authenticated with Spotify.")
        return

    # Get the host's active device
    active_device = get_active_device(sp_host)
    if not active_device:
        print("No active Spotify device found for the host.")
        return

    # Queue the song
    try:
        sp_host.add_to_queue(track_uri, device_id=active_device)
        print(f"Song {track_uri} added to the queue by scanner {session_id}.")
        # Notify the scanner that the song was added
        socketio.emit('song_added', {'track_uri': track_uri}, to=session_id)
    except Exception as e:
        print(f"Error adding song to queue: {e}")

@socketio.on('connect')
def on_connect():
    # Get session_id for the scanner or host
    session_id = session.get('session_id')

    if session_id:
        # Join a room named after the session_id
        join_room(session_id)
        print(f"Client joined room: {session_id}")

def emit_event(event, data):
    socketio.emit(event, data)

app.secret_key = secrets.token_hex(16)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
app.config['TOKEN_EXPIRATION'] = timedelta(minutes=30)
Session(app)

# Spotify credentials and auth
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
redirect_uri = 'http://hopon-aux.com/callback'  # Ensure this matches your Spotify app settings
scope="user-modify-playback-state user-read-playback-state"

sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_path='.spotifycache'
)

# Helper functions
def get_spotify_client():
    from flask import session
    token_info = session.get('token_info', None)
    if not token_info:
        return None

    # Check if token is expired and refresh if necessary
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    access_token = token_info['access_token']
    sp = spotipy.Spotify(auth=access_token)
    return sp

def get_active_device(sp_host):
    devices = sp_host.devices()
    for device in devices['devices']:
        if device['is_active']:
            return device['id']
    return None

# Import routes
from app import routes
import secrets