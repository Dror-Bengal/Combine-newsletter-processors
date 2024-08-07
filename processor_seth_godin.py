import json
from bs4 import BeautifulSoup
from flask import jsonify

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_block = extract_content_block(soup)
        
        output_json = {
            "content_blocks": [content_block]
        }
        
        return jsonify(output_json), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_content_block(soup):
    # Extract main image (if any)
    main_image = soup.find('img', class_='c24')
    image_url = main_image['src'] if main_image else ""

    # Extract main content
    main_content = extract_main_content(soup)

    content_block = {
        "text": main_content,
        "image": image_url,
        "link": "",
        "scoring": 1,
        "enrichment_text": "<placeholder>",
        "main_category": "Newsletter",
        "sub_category": "Seth Godin's Blog",
        "social_trend": "<placeholder>"
    }

    return content_block

def extract_main_content(soup):
    content_container = soup.find('div', class_='rssDesc')
    if not content_container:
        return ""

    # Extract title
    title = content_container.find('h2')
    title_text = title.get_text(strip=True) if title else ""

    # Extract paragraphs
    paragraphs = content_container.find_all('p')
    content_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    main_content = f"{title_text}\n\n{content_text}"
    return main_content

# No Flask app or route decorators in this file