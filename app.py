from flask import Flask, request, jsonify
from combined_processor import process_email
from celery import Celery
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Celery configuration
redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
celery = Celery('tasks', broker=redis_url, backend=redis_url)
celery.conf.update(
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
)

@app.route('/')
def home():
    logger.debug("Home route accessed")
    return "Newsletter Processor API is running!"

@app.route('/process-newsletter', methods=['POST'])
def process_newsletter():
    logger.debug(f"Received request data: {request.json}")
    data = request.json
    result, status_code = process_email(data)
    return jsonify(result), status_code

@app.route('/process_email', methods=['POST'])
def process_email_route():
    logger.debug(f"Received request data: {request.json}")
    data = request.json
    result, status_code = process_email(data)
    return jsonify(result), status_code

@app.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

# This line is important for Gunicorn to find your Flask application
application = app