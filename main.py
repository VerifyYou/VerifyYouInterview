import logging
import google.cloud.logging
import os

from flask import Flask
from flask import jsonify
from flask_cors import CORS

from user import user_app
from config_app import config_app

app = Flask(__name__)

app.register_blueprint(user_app)
app.register_blueprint(config_app)

@app.errorhandler(500)
def internal_error(error):
    return {"code": 500}, 500

@app.errorhandler(404)
def internal_error(error):
    return {"code": 404}, 404

@app.route("/_ah/warmup")
def warmup():
    """Served stub function returning no content.

    Your warmup logic can be implemented here (e.g. set up a database connection pool)

    Returns:
        An empty string, an HTTP code 200, and an empty object.
    """
    return "", 200, {}

allowed_origins = ["https://verifyyou.io", "https://verifyyou.com", "http://localhost:3000"]
CORS(app, resources={r"/*": {"origins": allowed_origins}}, methods=['GET', 'POST', 'OPTIONS'])

if __name__ == '__main__':
    # Run locally
    app.run(host="0.0.0.0", port=int(os.getenv('LOCAL_PORT')), debug=True)
else:
    google.cloud.logging.Client(project=os.getenv('PROJECT_ID')).setup_logging()
