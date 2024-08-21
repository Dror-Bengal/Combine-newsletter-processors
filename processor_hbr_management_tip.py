import logging
from bs4 import BeautifulSoup
from translator import translate_text
from newsletter_utils import process_content_block, determine_categories
from functools import lru_cache

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1000)
def cached_translate(text):
    return translate_text(text)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Harvard Business Review Management Tip of the Day",
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
    logger.debug("Starting to process HBR Management Tip email")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        if not meets_criteria(metadata):
            logger.info("Email does not meet the criteria for HBR Management Tip of the Day")
            return {"error": "Not an HBR Management Tip of the Day email"}, 400
        
        output_json = create_base_output_structure(metadata)
        
        logger.debug(f"Content HTML length: {len(content_html)}")
        
        soup = BeautifulSoup(content_html, 'html.parser')
        logger.debug(f"BeautifulSoup object created. Number of tags: {len(soup.find_all())}")

        content_block = extract_content(soup)
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

def meets_criteria(metadata):
    sender = metadata.get('sender', '')
    subject = metadata.get('subject', '')
    sender_name = metadata.get('Sender name', '')

    is_correct_sender = sender == "emailteam@emails.hbr.org"
    is_correct_subject = subject == "The Management Tip of the Day"
    is_correct_name = sender_name == "Harvard Business Review"
    
    logger.debug(f"Sender check: {is_correct_sender}, Subject check: {is_correct_subject}, Name check: {is_correct_name}")
    
    return is_correct_sender and is_correct_subject and is_correct_name

def extract_content(soup):
    try:
        main_content = soup.find('table', class_='row-content stack')
        
        if not main_content:
            logger.warning("Main content container not found")
            return None

        title = main_content.find('h1')
        title_text = title.get_text(strip=True) if title else ""

        content_div = main_content.find('div', style=lambda s: s and 'font-family:Georgia,Times,\'Times New Roman\',serif' in s)
        tip_paragraphs = content_div.find_all('p') if content_div else []
        tip_text = "\n\n".join([p.get_text(strip=True) for p in tip_paragraphs])

        source_div = main_content.find('div', style=lambda s: s and 'font-family:Helvetica Neue,Helvetica,Arial,sans-serif' in s)
        source_text = source_div.get_text(strip=True) if source_div else ""

        block = {
            "block_type": "article",
            "title": title_text,
            "body_text": f"{tip_text}\n\nSource: {source_text}",
            "image_url": "",
            "link_url": "",
        }
        
        processed_block = process_content_block(block)
        if processed_block['block_type'] != 'removed':
            processed_block['categories'] = determine_categories(processed_block)
            processed_block['translated_title'] = cached_translate(processed_block['title'])
            processed_block['translated_body_text'] = cached_translate(processed_block['body_text'])
        
        logger.debug(f"Processed content block: {processed_block}")
        return processed_block

    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return None

# No Flask app or route decorators in this file