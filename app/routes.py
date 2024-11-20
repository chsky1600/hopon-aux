from flask import render_template, url_for, send_file, request, redirect, flash, session, get_flashed_messages
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
    delete_session_set,
    insert_active_scanner
)

load_dotenv()
redis_client = redis.from_url(os.getenv('REDIS_URL'))

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
app.config['SESSION_PERMANENT'] = False
app.config['TOKEN_EXPIRATION'] = timedelta(minutes=30)

socketio = SocketIO(app, logger=False, engineio_logger=False)



@app.route('/')
def index():
    redis_status = test_connection()
    session_id = session.get('session_id')
    print(f"Session ID after /callback: {session_id}")
    logged_in = session.get('logged_in', False)
    current_token = None
    token_info = session.get('token_info')
    remaining_ttl = None

    session['logged_in'] = bool(token_info)
    print(f"logged_in: {session['logged_in']}")
    
    if session['logged_in']:
        current_token = get_valid_token(session_id)
        print(f"current_token is: {current_token}")
        # Get the remaining TTL for the current token
        remaining_ttl = redis_client.ttl(f"session_{session_id}")
        print(f"TTL for current token: {remaining_ttl} seconds")

        if remaining_ttl > 0:  # Ensure valid TTL
            # Calculate expiration timestamp
            expiration_timestamp = (datetime.now() + timedelta(seconds=remaining_ttl)).timestamp()
        elif remaining_ttl == -1:
            # Key exists but has no expiration
            print("Current token exists but has no TTL.")
            expiration_timestamp = None
        else:
            # Key does not exist or TTL is invalid
            print("Current token has expired or key is missing.")
            expiration_timestamp = None

    else:
        # Handle when the user is not logged in
        current_token = None
        expiration_timestamp = None
    
    return render_template(
    'index.html',
    logged_in=logged_in,
    current_token=current_token,
    remaining_ttl=remaining_ttl if remaining_ttl and remaining_ttl > 0 else 0,
    redis_status=redis_status
)

@app.route('/generate_qr')
def generate_qr():
    token = get_valid_token(session.get('session_id'))

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
    
    # get_flashed_messages()

    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            # Store active scanner name in Redis
            insert_active_scanner(session_id, name)
            # redis_client.sadd("active_scanners", name)
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
            error_message = str(e)
            if "No active device found" in error_message:
                flash("Awkward... seems like nothing's playing right now. Go tell your host to put something on!", 'error')  
            else:
                flash(f'Error adding song to queue: {e}', 'error')
    else:
        flash('No track URI provided.', 'error')

    return redirect(url_for('add_song', song_query=song_query))

@app.route('/login')
def login():
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    print(f"\n(logged in) Session ID: {session_id}\n")
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
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app)