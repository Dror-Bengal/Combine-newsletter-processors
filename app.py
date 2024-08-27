from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def extract_content(html_content, sender_name):
    soup = BeautifulSoup(html_content, 'html.parser')
    content = {
        "title": "",
        "image_url": "",
        "body_text": "",
        "link": "",
        "credit": sender_name
    }

    # Try to extract title
    title_elem = soup.find(['h1', 'h2'])
    if title_elem:
        content['title'] = title_elem.text.strip()

    # Try to extract image
    img_elem = soup.find('img')
    if img_elem and 'src' in img_elem.attrs:
        content['image_url'] = img_elem['src']

    # Try to extract body text (first paragraph or div)
    body_elem = soup.find(['p', 'div'])
    if body_elem:
        content['body_text'] = body_elem.text.strip()

    # Try to extract link
    link_elem = soup.find('a')
    if link_elem and 'href' in link_elem.attrs:
        content['link'] = link_elem['href']

    return content

@app.route('/process-newsletter', methods=['POST'])
def process_newsletter():
    try:
        data = request.json
        html_content = data.get('html_content', '')
        sender_name = data.get('sender_name', '')
        subject = data.get('subject', '')

        content = extract_content(html_content, sender_name)

        # If extraction failed, use the subject as title and full HTML as body
        if not content['title'] and not content['body_text']:
            content['title'] = subject
            content['body_text'] = html_content

        return jsonify(content), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)