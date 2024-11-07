from flask import render_template, url_for, send_file, request, redirect, flash, session
import qrcode
import io
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app import app, sp_oauth, get_spotify_client, get_active_device

# Authentication routes
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    session['logged_in'] = True
    return redirect(url_for('index'))

# Main routes
@app.route('/')
def index():
    logged_in = session.get('logged_in', False)
    return render_template('index.html', logged_in=logged_in)

@app.route('/qr_code')
def qr_code():
    # Data to encode in the QR code
    data = url_for('add_song', _external=True)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill='black', back_color='white')

    # Save the image in a bytes buffer
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

@app.route('/add_song', methods=['GET', 'POST'])
def add_song():
    sp_host = get_spotify_client()
    if not sp_host:
        flash('Host is not authenticated with Spotify.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        song_query = request.form.get('song_query')
        if song_query:
            # Use client credentials for searching
            client_credentials_manager = SpotifyClientCredentials(client_id=app.config['SPOTIFY_CLIENT_ID'], client_secret=app.config['SPOTIFY_CLIENT_SECRET'])
            sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            results = sp.search(q=song_query, type='track', limit=10)
            tracks = results['tracks']['items']
            return render_template('add_song.html', tracks=tracks)
        else:
            flash('Please enter a song query')
            return redirect(url_for('add_song'))
    return render_template('add_song.html')

@app.route('/queue_song', methods=['POST'])
def queue_song():
    sp_host = get_spotify_client()
    if not sp_host:
        flash('Host is not authenticated with Spotify.')
        return redirect(url_for('index'))

    active_device = get_active_device(sp_host)
    if not active_device:
        flash('No active device found. Please start playing music on your Spotify account.')
        return redirect(url_for('add_song'))

    track_uri = request.form.get('track_uri')
    if track_uri:
        try:
            sp_host.add_to_queue(track_uri, device_id=active_device)
            flash('Song added to the queue!')
        except spotipy.exceptions.SpotifyException as e:
            flash(f'Error adding song to queue: {e}')
    else:
        flash('No track URI provided.')

    return redirect(url_for('add_song'))