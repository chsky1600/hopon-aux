from flask import Flask, render_template, url_for, send_file, request, redirect, flash
import qrcode
import io
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

@app.route('/')
def index():
    return render_template('index.html')

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

    # Send the image file
    return send_file(img_io, mimetype='image/png')

@app.route('/add_song', methods=['GET', 'POST'])
def add_song():
    if request.method == 'POST':
        song_query = request.form.get('song_query')
        if song_query:
            results = sp.search(q=song_query, type='track', limit=10)
            tracks = results['tracks']['items']
            return render_template('add_song.html', tracks=tracks)
        else:
            flash('Please enter a song query')
            return redirect(url_for('add_song'))
    return render_template('add_song.html')

if __name__ == '__main__':
    app.run(debug=False, port=5002)
