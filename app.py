from flask import Flask, request, jsonify
from processor_v1 import process_email as process_creativity_daily
from processor_v2 import process_email as process_aotw
from processor_creative_bloq import process_email as process_creative_bloq

app = Flask(__name__)

@app.route('/process_email', methods=['POST'])
def process_email():
    data = request.get_json()
    
    if not data or 'metadata' not in data or 'sender' not in data['metadata']:
        return jsonify({"error": "Invalid JSON structure or missing 'sender' field"}), 400
    
    sender = data['metadata']['sender']
    
    if "adage@e.crainalerts.com" in sender:
        return process_creativity_daily(data)
    elif "newsletter@adsoftheworld.com" in sender:
        return process_aotw(data)
    elif "newsletter@email.creativebloq.com" in sender:
        return process_creative_bloq(data)
    else:
        return jsonify({"error": "Unknown newsletter source"}), 400

application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)