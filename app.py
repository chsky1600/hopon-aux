import os
from app import app

if __name__ == '__main__':
    # Get the port from the environment variable or use a default (e.g., 5000 for local testing)
    port = int(os.environ.get('PORT', 5002))
    # Run the app
    app.run(debug=False, host='0.0.0.0', port=port)