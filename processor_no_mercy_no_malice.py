import json
from bs4 import BeautifulSoup
from flask import jsonify
import re

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
        output_json = {
            "content_blocks": content_blocks
        }
        
        return jsonify(output_json), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_content_blocks(soup):
    content_blocks = []
    score = 1

    # Extract main image
    main_image = soup.find('img', src=re.compile(r'NoMercyNoMalice_masthead'))
    if main_image:
        content_blocks.append({
            "text": "",
            "image": main_image['src'],
            "link": "",
            "scoring": score,
            "enrichment_text": "<placeholder>",
            "main_category": "Newsletter",
            "sub_category": "<placeholder>",
            "social_trend": "<placeholder>"
        })
        score += 1

    # Extract content blocks
    for block in soup.find_all(['p', 'img']):
        content = {}

        if block.name == 'img':
            content['image'] = block.get('src', '')
            content['text'] = block.get('alt', '')
        else:
            content['text'] = block.text.strip()
            link = block.find('a')
            if link:
                content['link'] = link.get('href', '')

        if content.get('text') or content.get('image'):
            content['scoring'] = score
            content['enrichment_text'] = "<placeholder>"
            content['main_category'] = "Newsletter"
            content['sub_category'] = determine_sub_category(content.get('text', ''))
            content['social_trend'] = "<placeholder>"
            content_blocks.append(content)
            score += 1

    return content_blocks

def determine_sub_category(text):
    categories = {
        'Business': ['business', 'company', 'market'],
        'Technology': ['tech', 'technology', 'digital'],
        'Sports': ['Olympics', 'athletes', 'sports'],
        'Media': ['TV', 'streaming', 'audience'],
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

# No Flask app or route decorators in this file