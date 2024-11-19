from flask import render_template, url_for, send_file, request, redirect, flash, session
import qrcode, redis, io, uuid, spotipy, os
from spotipy.oauth2 import SpotifyClientCredentials
from app import app, sp_oauth, get_spotify_client, get_active_device
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
from db.redis import (
    test_connection,
    insert_qr_token,
    get_valid_token,
    delete_session_set
)

load_dotenv()
redis_client = redis.from_url(os.getenv('REDIS_URL'))

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
app.config['SESSION_PERMANENT'] = False
app.config['TOKEN_EXPIRATION'] = timedelta(minutes=30)

socketio = SocketIO(app, logger=False, engineio_logger=False)

def generate_token():
    """
    Generate a new QR token, store it in Redis, and emit it to clients.
    """
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id

    token = str(uuid.uuid4())
    insert_qr_token(session_id, token, app.config['TOKEN_EXPIRATION'])

    socketio.emit('new_token', {'token': token})
    return token

@app.route('/')
def index():
    redis_status = test_connection()
    session_id = session.get('session_id')
    logged_in = session.get('logged_in', False)
    current_token, expiration_timestamp = None, None
    token_info = session.get('token_info')

    session['logged_in'] = bool(token_info)

    if session['logged_in']:

        current_token = get_valid_token(session_id)

        if current_token:
            expiration_time = redis_client.ttl(f"qr_token:{current_token}")
            expiration_timestamp = datetime.now() + timedelta(seconds=expiration_time)
        else:
            current_token = generate_token()
            expiration_timestamp = datetime.now() + app.config['TOKEN_EXPIRATION']
        
    return render_template(
        'index.html',
        logged_in=logged_in,
        current_token=current_token,
        token_expiration=expiration_timestamp,
        redis_status=redis_status
    )

@app.route('/generate_qr')
def generate_qr():
    token = get_valid_token(session.get('session_id'))
    if not token:
        token = generate_token()

    data = f"http://127.0.0.1:5002/scan_qr?token={token}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

@app.route('/scan_qr', methods=['GET', 'POST'])
def scan_qr():
    session_id = session.get('session_id')
    token = request.args.get('token')
    print(token)
    
    if token and get_valid_token(session_id) == token:
        session['qr_token'] = token
        return redirect(url_for('input_name'))
    else:
        flash('QR code has expired or is invalid.')
        return redirect(url_for('index'))

@app.route('/input_name', methods=['GET', 'POST'])
def input_name():
    token = session.get('qr_token')
    session_id = session.get('session_id')

    if not token or get_valid_token(session_id) != token:
        session.clear()
        flash('Session has expired. Please scan the QR code again.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            # Store active scanner name in Redis
            redis_client.sadd("active_scanners", name)
            socketio.emit('new_scanner', {'name': name})
            return redirect(url_for('add_song'))
        else:
            flash('Name is required.')
    return render_template('input_name.html')

@app.route('/add_song', methods=['GET', 'POST'])
def add_song():
    token = session.get('qr_token')
    session_id = session.get('session_id')

    if not token or get_valid_token(session_id) != token:
        session.clear()
        flash('Session has expired. Please scan the QR code again.')
        return redirect(url_for('index'))

    sp_host = get_spotify_client()
    if not sp_host:
        flash('Host is not authenticated with Spotify.')
        return redirect(url_for('index'))

    song_query = request.form.get('song_query') or request.args.get('song_query')
    tracks = None
    if song_query:
        client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        results = sp.search(q=song_query, type='track', limit=10)
        tracks = results['tracks']['items']
    elif request.method == 'POST' and not song_query:
        flash('Please enter a song query')
        return redirect(url_for('add_song'))
    return render_template('add_song.html', tracks=tracks, song_query=song_query)

@app.route('/queue_song', methods=['POST'])
def queue_song():
    sp_host = get_spotify_client()
    if not sp_host:
        flash('Host is not authenticated with Spotify.')
        return redirect(url_for('index'))

    active_device = get_active_device(sp_host)

    track_uri = request.form.get('track_uri')
    song_query = request.form.get('song_query')

    if track_uri:
        try:
            sp_host.add_to_queue(track_uri, device_id=active_device)
            flash('Song added to the queue!')
        except spotipy.exceptions.SpotifyException as e:
            flash(f'Error adding song to queue: {e}')
    else:
        flash('No track URI provided.')

    return redirect(url_for('add_song', song_query=song_query))

@app.route('/login')
def login():
    session_id = session.get('session_id')
    print(f"\n(logged in) Session ID: {session_id}\n")
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    session['logged_in'] = True
    session.permanent = False
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/logout')
def logout():
    session_id = session.get('session_id')
    print(f"\n(as logging out) Session ID: {session_id}\n")

    delete_session_set(session_id)

    session.clear()
    session['logged_in'] = False
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app)