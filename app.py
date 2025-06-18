import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Import routes after app creation to avoid circular imports
from api_routes import api_bp
from flask import render_template

# Register blueprints
app.register_blueprint(api_bp)

@app.route('/')
def index():
    """Main page with API documentation"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Test interface for the API"""
    return render_template('test.html')

@app.errorhandler(404)
def not_found(error):
    return {"error": "Endpoint not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal server error"}, 500
