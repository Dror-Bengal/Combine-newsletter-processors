import logging
from bs4 import BeautifulSoup
from translator import translate_text
from newsletter_utils import process_content_block, determine_categories
from functools import lru_cache

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1000)
def cached_translate(text):
    return translate_text(text)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Simon Sinek's Notes to Inspire",
            "sender_email": metadata.get('sender', ''),
            "sender_name": metadata.get('Sender name', ''),
            "date_sent": metadata.get('date', ''),
            "subject": metadata.get('subject', ''),
            "email_id": metadata.get('message-id', ''),
            "translated_subject": cached_translate(metadata.get('subject', ''))
        },
        "content": {
            "content_blocks": []
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
        
        if not is_simon_sinek_email(metadata):
            logger.info("Email is not from Simon Sinek")
            return {"error": "Not a Simon Sinek email"}, 400
        
        output_json = create_base_output_structure(metadata)
        
        logger.debug(f"Content HTML length: {len(content_html)}")
        
        soup = BeautifulSoup(content_html, 'html.parser')
        logger.debug(f"BeautifulSoup object created. Number of tags: {len(soup.find_all())}")

        content_block = extract_content_block(soup)
        if content_block:
            output_json['content']['content_blocks'] = [content_block]
            logger.debug(f"Processed output: {output_json}")
            return output_json, 200
        else:
            logger.error("Failed to extract content")
            return {"error": "Failed to extract content"}, 400

    except Exception as e:
        logger.exception("Unexpected error in process_email")
        return {"error": str(e)}, 500

def is_simon_sinek_email(metadata):
    sender = metadata.get('sender', '').lower()
    sender_name = metadata.get('Sender name', '').lower()
    
    is_correct_sender = 'inspireme@simonsinek.com' in sender
    is_correct_name = 'simon sinek' in sender_name
    
    logger.debug(f"Sender check: {is_correct_sender}, Name check: {is_correct_name}")
    
    return is_correct_sender and is_correct_name

def extract_content_block(soup):
    logger.debug("Extracting content block")
    try:
        # Extract main image
        main_image = soup.find('img', class_='stretch-on-mobile')
        image_url = main_image['src'] if main_image else ""

        # Extract main content
        content_container = soup.find('div', id=lambda x: x and x.startswith('hs_cos_wrapper_module-0-0-1_'))
        if not content_container:
            logger.warning("Content container not found")
            return None

        main_content = content_container.get_text(strip=True)

        block = {
            "block_type": "article",
            "title": "Simon Sinek's Note to Inspire",
            "body_text": main_content,
            "image_url": image_url,
            "link_url": "",
        }
        
        processed_block = process_content_block(block)
        if processed_block['block_type'] != 'removed':
            processed_block['categories'] = determine_categories(processed_block)
            processed_block['translated_title'] = cached_translate(processed_block['title'])
            processed_block['translated_body_text'] = cached_translate(processed_block['body_text'])
            processed_block['score'] = calculate_score(processed_block)
        
        logger.debug(f"Processed content block: {processed_block}")
        return processed_block

    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return None

def calculate_score(block):
    score = 0
    
    # Score based on content length
    text_length = len(block.get('body_text', ''))
    score += min(text_length // 10, 50)  # Max 50 points for length
    
    # Score for presence of categories
    score += len(block.get('categories', [])) * 10  # 10 points per category
    
    # Score for presence of image
    if block.get('image_url'):
        score += 20
    
    # Normalize score to 0-100 range
    return min(score, 100)

# No Flask app or route decorators in this file