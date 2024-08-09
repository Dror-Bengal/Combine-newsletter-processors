from flask import Flask, request, jsonify
from processor_v1 import process_email as process_creativity_daily
from processor_v2 import process_email_content as process_aotw
from processor_creative_bloq import process_email as process_creative_blog
from processor_campaign_brief import process_email as process_campaign_brief
from processor_adweek_agency import process_email as process_adweek_agency_daily
from processor_adweek_daily import process_email as process_adweek_daily
from processor_no_mercy_no_malice import process_email as process_no_mercy_no_malice
from processor_seth_godin import process_email as process_seth_godin
from processor_simon_sinek import process_email as process_simon_sinek
from processor_hbr_management_tip import process_email as process_hbr_management_tip
from processor_dorie_clark import process_email as process_dorie_clark
from translator import translate_content_block, translate_content_block_async
import logging
import json
import os
from celery import Celery
from celery.exceptions import OperationalError

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379')
logger.debug(f"Using Redis URL: {redis_url}")

celery = Celery('tasks', broker=redis_url, backend=redis_url)

@app.route('/process_email', methods=['POST'])
def process_email():
    logger.debug(f"Received request data: {request.data}")
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return jsonify({"error": "Invalid JSON format"}), 400

    if not data:
        logger.error("No JSON data received")
        return jsonify({"error": "No JSON data received"}), 400
    
    logger.debug(f"Parsed JSON data: {data}")
    
    if 'metadata' not in data:
        logger.error("Missing 'metadata' field in JSON")
        return jsonify({"error": "Missing 'metadata' field"}), 400
    
    if 'sender' not in data['metadata']:
        logger.error("Missing 'sender' field in metadata")
        return jsonify({"error": "Missing 'sender' field in metadata"}), 400
    
    sender = data['metadata']['sender']
    subject = data['metadata'].get('subject', '')
    sender_name = data['metadata'].get('Sender name', '')
    logger.debug(f"Sender: {sender}, Subject: {subject}, Sender name: {sender_name}")
    
    try:
        result = None
        if "adage@e.crainalerts.com" in sender:
            logger.debug("Processing as Creativity Daily")
            result, status_code = process_creativity_daily(data)
        elif "newsletter@adsoftheworld.com" in sender:
            logger.debug("Processing as Ads of the World")
            try:
                task = process_aotw.delay(data)
                logger.debug(f"Task created with id: {task.id}")
                return jsonify({"task_id": task.id}), 202
            except OperationalError as e:
                logger.error(f"Celery OperationalError: {str(e)}")
                return jsonify({"error": "Failed to queue task. Celery may be unavailable."}), 503
            except Exception as e:
                logger.error(f"Failed to queue task: {str(e)}")
                return jsonify({"error": "Failed to process request"}), 500
        elif "creativebloq@smartbrief.com" in sender:
            logger.debug("Processing as Creative Bloq")
            result, status_code = process_creative_blog(data)
        elif "no-reply@campaignbrief.com" in sender or "no-reply@campaignbrief.co.nz" in sender:
            logger.debug("Processing as Campaign Brief")
            result, status_code = process_campaign_brief(data)
        elif "email@email.adweek.com" in sender:
            if "Adweek Daily" in data['metadata'].get('Sender name', ''):
                logger.debug("Processing as Adweek Daily")
                result, status_code = process_adweek_daily(data)
            else:
                logger.debug("Processing as Adweek Advertising & Agency Daily")
                result, status_code = process_adweek_agency_daily(data)
        elif "nomercynomalice@mail.profgalloway.com" in sender:
            logger.debug("Processing as No Mercy No Malice")
            result, status_code = process_no_mercy_no_malice(data)
        elif "notify@sethgodin.com" in sender:
            logger.debug("Processing as Seth Godin's Blog")
            result, status_code = process_seth_godin(data)
        elif "inspireme@simonsinek.com" in sender:
            logger.debug("Processing as Simon Sinek's Notes to Inspire")
            result, status_code = process_simon_sinek(data)
        elif sender == "emailteam@emails.hbr.org" and subject == "The Management Tip of the Day" and sender_name == "Harvard Business Review":
            logger.debug("Processing as Harvard Business Review Management Tip")
            result, status_code = process_hbr_management_tip(data)
        elif "dorie@dorieclark.com" in sender:
            logger.debug("Processing as Dorie Clark newsletter")
            result, status_code = process_dorie_clark(data)
        else:
            logger.error(f"Unknown newsletter source: {sender}")
            return jsonify({"error": f"Unknown newsletter source: {sender}"}), 400

        if result and isinstance(result, dict) and 'content_blocks' in result:
            for block in result['content_blocks']:
                translate_content_block_async.delay(block, target_language='he')
            
            # Don't wait for translation results here
            return jsonify({"message": "Email processed and translation started", "result": result}), 202

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Unexpected error in process_email: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    try:
        task = process_aotw.AsyncResult(task_id)
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': 'Task is pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'status': task.info.get('status', '')
            }
            if 'result' in task.info:
                response['result'] = task.info['result']
        else:
            response = {
                'state': task.state,
                'status': str(task.info)
            }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        return jsonify({"error": "Failed to check task status"}), 500

@app.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

# Ensure all response data is JSON serializable
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        return json.JSONEncoder.default(self, obj)

app.json_encoder = JSONEncoder

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

application = app