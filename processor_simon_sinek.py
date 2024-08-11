import json
from bs4 import BeautifulSoup
import logging
from translator import translate_text
import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Simon Sinek's Notes to Inspire",
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
    logger.debug("Starting to process Simon Sinek's 'Notes to Inspire' email")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        output_json = create_base_output_structure(metadata)
        
        soup = BeautifulSoup(content_html, 'html.parser')

        # Convert HTML to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False
        output_json['content']['main_content_text'] = h.handle(content_html)
        output_json['content']['translated_main_content_text'] = translate_text(output_json['content']['main_content_text'])

        content_block = extract_content_block(soup)
        output_json['content']['content_blocks'] = [content_block]
        
        logger.debug("Successfully processed Simon Sinek's email")
        return output_json, 200

    except Exception as e:
        logger.exception("Unexpected error in process_email")
        return {"error": str(e)}, 500

def extract_content_block(soup):
    logger.debug("Extracting content block")
    
    # Extract main image
    main_image = soup.find('img', class_='stretch-on-mobile')
    image_url = main_image['src'] if main_image else ""

    # Extract main content
    content_container = soup.find('div', id=lambda x: x and x.startswith('hs_cos_wrapper_module-0-0-1_'))
    if not content_container:
        logger.warning("Content container not found")
        return {}

    main_content = content_container.get_text(strip=True)

    content_block = {
        "block_type": "inspiration",
        "title": "Simon Sinek's Note to Inspire",
        "translated_title": translate_text("Simon Sinek's Note to Inspire"),
        "description": main_content[:200] + "..." if len(main_content) > 200 else main_content,
        "translated_description": translate_text(main_content[:200] + "..." if len(main_content) > 200 else main_content),
        "body_text": main_content,
        "translated_body_text": translate_text(main_content),
        "image_url": image_url,
        "link_url": "",  # No specific link in this newsletter format
        "category": "Notes to Inspire",
        "subcategory": "Daily Inspiration",
        "social_trend": generate_social_trend(main_content),
        "translated_social_trend": translate_text(generate_social_trend(main_content))
    }

    return content_block

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the content
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#SimonSinekInspire"

# No Flask app or route decorators in this file