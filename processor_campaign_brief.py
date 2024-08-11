from bs4 import BeautifulSoup
import logging
import re
from translator import translate_text
import html2text

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Campaign Brief",
            "sender_email": metadata.get('sender', ''),
            "sender_name": metadata.get('Sender name', ''),
            "date_sent": metadata.get('date', ''),
            "subject": metadata.get('subject', ''),
            "email_id": metadata.get('message-id', ''),
            "translated_subject": translate_text(metadata.get('subject', ''))
        },
        "content": {
            "main_content_html": metadata['content']['html'],
            "main_content_text": "",
            "translated_main_content_text": "",
            "content_blocks": []
        },
        "additional_info": {
            "attachments": [],
            "engagement_metrics": {}
        },
        "translation_info": {
            "translated_language": "he",
            "translation_method": "Google Translate API"
        }
    }

def process_email(data):
    logging.debug(f"Received data in process_email: {data}")
    try:
        if not data or 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        output_json = create_base_output_structure(metadata)

        # Convert HTML to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False
        output_json['content']['main_content_text'] = h.handle(content_html)
        output_json['content']['translated_main_content_text'] = translate_text(output_json['content']['main_content_text'])
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        output_json['content']['content_blocks'] = content_blocks

        logging.debug(f"Processed output: {output_json}")
        return output_json, 200

    except Exception as e:
        logging.error(f"Error processing email: {str(e)}")
        return {"error": str(e)}, 500

def extract_content_blocks(soup):
    content_blocks = []
    score = 1

    logging.debug("Starting to extract content blocks")

    # Find the table with id="rssColumn"
    rss_column = soup.find('table', id='rssColumn')
    logging.debug(f"Found rssColumn: {rss_column is not None}")

    if rss_column:
        # Find all content blocks within the rssColumn
        blocks = rss_column.find_all('div', style=lambda value: value and 'text-align: left;color: #656565;min-width: 300px;' in value)
        logging.debug(f"Found {len(blocks)} potential content blocks")

        for block in blocks:
            content = {
                "block_type": "article",
                "scoring": score
            }

            # Extract image
            img_tag = block.find('img', class_='mc-rss-item-img')
            if img_tag:
                content['image_url'] = img_tag.get('src', '')
                logging.debug(f"Found image: {content['image_url']}")

            # Extract headline and link
            headline_tag = block.find('a', style=lambda value: value and "font-family: 'Oswald'" in value)
            if headline_tag:
                content['title'] = headline_tag.text.strip()
                content['translated_title'] = translate_text(content['title'])
                content['link_url'] = headline_tag.get('href', '')
                logging.debug(f"Found headline: {content['title']}")

            # Extract description
            description_tag = block.find('div', id='rssContent')
            if description_tag:
                content['description'] = description_tag.text.strip()
                content['translated_description'] = translate_text(content['description'])
                content['body_text'] = content['description']
                content['translated_body_text'] = content['translated_description']
                logging.debug(f"Found description: {content['description'][:50]}...")

            # Add other required fields
            content['category'] = "Newsletter"
            content['subcategory'] = determine_sub_category(content.get('title', ''))
            content['social_trend'] = generate_social_trend(content.get('title', ''))
            content['translated_social_trend'] = translate_text(content['social_trend'])

            if content.get('title') and (content.get('image_url') or content.get('link_url')):
                content_blocks.append(content)
                score += 1
                logging.debug(f"Added content block {score}")
            else:
                logging.debug("Skipped incomplete content block")

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