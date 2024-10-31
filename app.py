from flask import Flask, render_template, url_for, send_file
import qrcode
import io

app = Flask(__name__)

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
    # Implementation of add_song route
    print("Test Mark")

if __name__ == '__main__':
    app.run(debug=False, port=5002)
