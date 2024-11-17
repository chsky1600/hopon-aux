# app/__init__.py

from flask import Flask
from flask_session import Session
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import secrets
from datetime import timedelta

load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')

#TODO: session config token to be server-side in prod 
app.secret_key = secrets.token_hex(16)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
Session(app)

# Spotify credentials and auth
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
redirect_uri = 'https://hopon-1c8107845ac3.herokuapp.com/callback'  # Ensure this matches your Spotify app settings
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