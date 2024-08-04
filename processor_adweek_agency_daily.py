import json
from bs4 import BeautifulSoup
from flask import jsonify
import re

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        metadata = {
            "date": data['metadata'].get('date'),
            "sender": data['metadata'].get('sender'),
            "subject": data['metadata'].get('subject'),
            "Sender name": data['metadata'].get('Sender name')
        }
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }
        
        return jsonify(output_json), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_content_blocks(soup):
    content_blocks = []
    score = 1
    seen_content = set()

    # Find all potential content blocks
    blocks = soup.find_all(['table', 'div'], class_=['em_wrapper'])

    for block in blocks:
        # Extract title
        title_elem = block.find(['span', 'td'], class_='em_font_18')
        if title_elem and title_elem.a:
            title = title_elem.a.text.strip()
            link = title_elem.a.get('href', '')
        else:
            continue  # Skip blocks without a title

        # Check for duplicates
        if title in seen_content:
            continue
        seen_content.add(title)

        # Extract image
        img_elem = block.find('img', class_='em_full_img')
        image = img_elem['src'] if img_elem else ''

        # Extract description
        desc_elem = block.find(['span', 'td'], class_='em_font_15')
        description = desc_elem.text.strip() if desc_elem else ''

        # Create content block
        content_block = {
            "text": title,
            "link": link,
            "image": image,
            "description": description,
            "enrichment_text": generate_enrichment_text(title),
            "main_category": "Newsletter",
            "sub_category": determine_sub_category(title),
            "social_trend": generate_social_trend(title),
            "scoring": score
        }

        content_blocks.append(content_block)
        score += 1

    return content_blocks

def generate_enrichment_text(text):
    return f"Enriched version of: {text[:50]}..."

def determine_sub_category(text):
    categories = {
        'Agency': ['agency', 'firm', 'company'],
        'Campaign': ['campaign', 'ad', 'commercial'],
        'Brand': ['brand', 'product', 'company'],
        'Digital': ['digital', 'online', 'social media'],
        'Creative': ['creative', 'design', 'art'],
        'Media': ['media', 'publisher', 'platform'],
        'Marketing': ['marketing', 'strategy', 'promotion']
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the title
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#AdweekTrend"

# Flask route and app.run() should be in the main app.py file, not here