from flask import render_template, url_for, send_file, request, redirect, flash, session
import qrcode, time, threading, io, uuid, spotipy, os
from spotipy.oauth2 import SpotifyClientCredentials
from app import app, sp_oauth, get_spotify_client, get_active_device
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit

load_dotenv()
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
app.config['SESSION_PERMANENT'] = False

socketio = SocketIO(app, logger=False, engineio_logger=False)

def ensure_session_initialized():
    if 'qr_tokens' not in app.config:
        app.config['qr_tokens'] = {}
    if 'active_scanners' not in app.config:
        app.config['active_scanners'] = []

def generate_token():
    with app.app_context():
        ensure_session_initialized() 
        token = str(uuid.uuid4())
        expiration_time = datetime.now() + timedelta(minutes=30)
        app.config['qr_tokens'][token] = expiration_time
        #print(f"Generated QR Token: {token}, Expires at: {expiration_time}")

def remove_expired_tokens():
    with app.app_context():
        ensure_session_initialized() 
        current_time = datetime.now()
        logged_in = session.get('logged_in', False)
        expired_tokens = [token for token, exp_time in app.config['qr_tokens'].items() if exp_time <= current_time or not logged_in]
        for token in expired_tokens:
            del app.config['qr_tokens'][token]
            #print(f"Removed expired token: {token}")
        #print(f"Current QR Tokens: {app.config['qr_tokens']}")

# Start the background tasks
# threading.Thread(target=generate_token, daemon=True).start()
# threading.Thread(target=remove_expired_tokens, daemon=True).start()

# Authentication routes
@app.route('/login')
def login():
    ensure_session_initialized()
    #print(f"\nCurrent session: {session}")
    #print(f"Token info: {app.config['qr_tokens']}\n")
    auth_url = sp_oauth.get_authorize_url()
    session['logged_in'] = True  # Set the logged_in session variable to True
    session.permanent = False  # Mark the session as permanent
    # print(f"\n Session logged_in set to: {session['logged_in']}\n")
    return redirect(auth_url)

@app.route('/logout')
def logout():
    token = session.get('qr_token')
    if token and token in app.config['qr_tokens']:
        with app.app_context():
            del app.config['qr_tokens'][token]

    session.clear()
    remove_expired_tokens()
    app.config.pop('qr_tokens', None)
    app.config.pop('active_scanners', None)
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('index'))

# Main routes
@app.route('/')
def index():
    ensure_session_initialized()
    if app.config['qr_tokens'] == {}:
        generate_token()
    # print(f"\nCurrent session: {session}")
    print(f"\n\nToken info: {app.config['qr_tokens']}\n\n")
    token_info = session.get('token_info')
    logged_in = session.get('logged_in', False)

    if token_info:
        session['logged_in'] = True
    else:
        session['logged_in'] = False
    
    # print(f"\nSession logged_in retrieved as: {logged_in}\n")
    
    # print(f"\n {token_info} \n")
    valid_qr_tokens = {token: exp_time for token, exp_time in app.config['qr_tokens'].items() if exp_time > datetime.now()}
    return render_template('index.html', logged_in=logged_in, qr_tokens=app.config['qr_tokens'], active_scanners=app.config['active_scanners'])

@app.route('/generate_qr')
def generate_qr():
    token = next(iter(app.config['qr_tokens']), None)

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

    # print(f"\n Redirect URI with QR UUID: {data}\n") # REMOVE on prod

    return send_file(img_io, mimetype='image/png')

@app.route('/scan_qr', methods=['GET', 'POST'])
def scan_qr():
    token = request.args.get('token')
    if token in app.config['qr_tokens'] and app.config['qr_tokens'][token] > datetime.now():
        session['qr_token'] = token
        return redirect(url_for('input_name'))
    else:
        flash('QR code has expired.')
        return redirect(url_for('index'))
    
@app.route('/input_name', methods=['GET', 'POST'])
def input_name():

    token = session.get('qr_token')
    if not token or token not in app.config['qr_tokens'] or app.config['qr_tokens'][token] <= datetime.now():
        session.clear()
        flash('Session has expired. Please scan the QR code again.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            app.config['active_scanners'].append(name)
            socketio.emit('new_scanner', {'name': name})  # Emit event to notify clients
            return redirect(url_for('add_song'))
        else:
            flash('Name is required.')
            return redirect(url_for('input_name'))
    return render_template('input_name.html')

@app.route('/add_song', methods=['GET', 'POST'])
def add_song():

    for i in app.config['active_scanners']:
        print(f"\nActive Scanner: {app.config['active_scanners']}\n")

    token = session.get('qr_token')
    if not token or token not in app.config['qr_tokens'] or app.config['qr_tokens'][token] <= datetime.now():
        session.clear()
        flash('Session has expired. Please scan the QR code again.')
        return redirect(url_for('index'))
    
    sp_host = get_spotify_client()
    if not sp_host:
        flash('Host is not authenticated with Spotify.')
        return redirect(url_for('index'))

    # Get the song_query from form data or query parameters
    song_query = request.form.get('song_query') or request.args.get('song_query')
    tracks = None
    if song_query:
        # Use client credentials for searching
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

    # Redirect back to add_song with the song_query
    return redirect(url_for('add_song', song_query=song_query))


# index --> input_name --> add_song

if __name__ == '__main__':
    socketio.run(app)