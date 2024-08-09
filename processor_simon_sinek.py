import json
from bs4 import BeautifulSoup
import logging
from translator import translate_text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_email(data):
    logger.debug("Starting to process Simon Sinek's 'Notes to Inspire' email")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_block = extract_content_block(soup)
        
        output_json = {
            "metadata": metadata,
            "content_blocks": [content_block]
        }
        
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

    # Translate content
    try:
        translated_content = translate_text(main_content)
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        translated_content = main_content

    content_block = {
        "text": main_content,
        "translated_text": translated_content,
        "image": image_url,
        "link": "",  # No specific link in this newsletter format
        "scoring": 1,
        "enrichment_text": "",  # No specific enrichment for this format
        "main_category": "Notes to Inspire",
        "sub_category": "Daily Inspiration",
        "social_trend": generate_social_trend(main_content)
    }

    return content_block

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the content
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#SimonSinekInspire"

# No Flask app or route decorators in this file