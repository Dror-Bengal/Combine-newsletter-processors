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

    # Extract main image
    main_image = soup.find('img', src=re.compile(r'NoMercyNoMalice_masthead'))
    if main_image:
        content_blocks.append({
            "text": "",
            "image": main_image['src'],
            "link": "",
            "scoring": 1,
            "enrichment_text": "<placeholder>",
            "main_category": "Newsletter",
            "sub_category": "Header",
            "social_trend": "<placeholder>"
        })

    # Extract main content
    main_content = extract_main_content(soup)
    if main_content:
        content_blocks.append({
            "text": main_content,
            "image": "",
            "link": "",
            "scoring": 2,
            "enrichment_text": "<placeholder>",
            "main_category": "Newsletter",
            "sub_category": "Main Content",
            "social_trend": "<placeholder>"
        })

    return content_blocks

def extract_main_content(soup):
    # Find the main content container
    content_container = soup.find('tr', id='content-blocks')
    if not content_container:
        return ""

    # Extract all text from paragraphs within the content container
    paragraphs = content_container.find_all('p')
    main_content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    return main_content

# No Flask app or route decorators in this file