from flask import Flask, request, jsonify
from combined_processor import process_email

app = Flask(__name__)

@app.route('/process-newsletter', methods=['POST'])
def process_newsletter():
    data = request.json
    result, status_code = process_email(data)
    return jsonify(result), status_code

if __name__ == '__main__':
    app.run(debug=True)