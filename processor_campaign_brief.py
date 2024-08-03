from flask import jsonify
from bs4 import BeautifulSoup
import logging
import re

logging.basicConfig(level=logging.DEBUG)

def process_email(data):
    logging.debug(f"Received data in process_email: {data}")
    try:
        if not data or 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)

        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }

        logging.debug(f"Processed output: {output_json}")
        return jsonify(output_json), 200

    except Exception as e:
        logging.error(f"Error processing email: {str(e)}")
        return jsonify({"error": str(e)}), 500

def extract_content_blocks(soup):
    content_blocks = []
    score = 1

    # Find the table with id="rssColumn"
    rss_column = soup.find('table', id='rssColumn')
    if rss_column:
        # Find all content blocks within the rssColumn
        for block in rss_column.find_all('div', style=lambda value: value and 'padding-bottom: 10px;' in value):
            content = {}

            # Extract image
            img_tag = block.find('img', class_='mc-rss-item-img')
            if img_tag:
                content['image'] = img_tag.get('src', '')

            # Extract headline and link
            headline_tag = block.find('a', style=lambda value: value and "font-family: 'Oswald'" in value)
            if headline_tag:
                content['text'] = headline_tag.text.strip()
                content['link'] = headline_tag.get('href', '')

            # Extract description
            description_tag = block.find('div', id='rssContent')
            if description_tag:
                content['description'] = description_tag.text.strip()

            # Add other required fields
            content['scoring'] = score
            content['main_category'] = "Newsletter"
            content['sub_category'] = determine_sub_category(content.get('text', ''))
            content['social_trend'] = generate_social_trend(content.get('text', ''))

            if content.get('text') and (content.get('image') or content.get('link')):
                content_blocks.append(content)
                score += 1

    logging.debug(f"Extracted {len(content_blocks)} content blocks")
    return content_blocks

def determine_sub_category(text):
    categories = {
        'Advertising': ['ad', 'campaign', 'creative'],
        'Awards': ['award', 'winner', 'ceremony'],
        'Industry News': ['agency', 'appointment', 'launch'],
        'Production': ['film', 'production', 'director'],
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the headline
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#CampaignBrief"

# No Flask app or route decorators in this file