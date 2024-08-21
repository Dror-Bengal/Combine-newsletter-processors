import logging
from bs4 import BeautifulSoup
import re
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
            "source_name": "No Mercy No Malice",
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
    logger.debug("Starting to process No Mercy No Malice email")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        if not is_no_mercy_no_malice_email(metadata):
            logger.info("Email is not from No Mercy No Malice")
            return {"error": "Not a No Mercy No Malice email"}, 400
        
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

def is_no_mercy_no_malice_email(metadata):
    sender = metadata.get('sender', '').lower()
    sender_name = metadata.get('Sender name', '').lower()
    
    is_correct_sender = 'nomercynomalice@mail.profgalloway.com' in sender
    is_correct_name = 'scott galloway' in sender_name
    
    logger.debug(f"Sender check: {is_correct_sender}, Name check: {is_correct_name}")
    
    return is_correct_sender and is_correct_name

def extract_content_block(soup):
    logger.debug("Extracting content block")
    try:
        content_container = soup.find('tr', id='content-blocks')
        if not content_container:
            logger.warning("Main content container not found")
            return None

        paragraphs = content_container.find_all('p')
        main_content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        main_content = re.sub(r'\nP\.S\..+', '', main_content, flags=re.DOTALL)
        main_content = re.sub(r'\nP\.P\.S\..+', '', main_content, flags=re.DOTALL)

        # Extract title from the first paragraph or use a default
        title = paragraphs[0].get_text(strip=True)[:100] if paragraphs else "No Mercy No Malice Insights"

        block = {
            "block_type": "article",
            "title": title,
            "body_text": main_content,
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