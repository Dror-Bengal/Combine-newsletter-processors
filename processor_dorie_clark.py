import logging
from bs4 import BeautifulSoup
from translator import translate_text
import html2text
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
            "source_name": "Dorie Clark Newsletter",
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
    logger.debug("Starting to process Dorie Clark newsletter")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        if not is_dorie_clark_newsletter(metadata):
            logger.info("Email is not from Dorie Clark")
            return {"error": "Not a Dorie Clark newsletter"}, 400
        
        output_json = create_base_output_structure(metadata)
        
        logger.debug(f"Content HTML length: {len(content_html)}")
        
        soup = BeautifulSoup(content_html, 'html.parser')
        logger.debug(f"BeautifulSoup object created. Number of tags: {len(soup.find_all())}")

        content_blocks = extract_content_blocks(soup)
        output_json['content']['content_blocks'] = content_blocks
        
        logger.debug(f"Number of content blocks extracted: {len(content_blocks)}")
        
        logger.debug(f"Processed output: {output_json}")
        return output_json, 200

    except Exception as e:
        logger.exception("Unexpected error in process_email")
        return {"error": str(e)}, 500

def is_dorie_clark_newsletter(metadata):
    sender = metadata.get('sender', '').lower()
    sender_name = metadata.get('Sender name', '').lower()
    
    is_correct_sender = 'dorie@dorieclark.com' in sender
    is_correct_name = 'dorie clark' in sender_name
    
    logger.debug(f"Sender check: {is_correct_sender}, Name check: {is_correct_name}")
    
    return is_correct_sender and is_correct_name

def extract_content_blocks(soup):
    content_blocks = []
    
    main_content_div = soup.find('div', class_='message-content')
    if main_content_div:
        content = []
        in_ad_section = False
        ad_counter = 0
        
        for elem in main_content_div.find_all(['p', 'ul', 'ol', 'h2']):
            text = elem.get_text(strip=True)
            
            if "***" in text:
                ad_counter += 1
                in_ad_section = ad_counter % 2 != 0  # Toggle ad section on odd counts
                continue
            
            if not in_ad_section:
                if elem.name == 'p':
                    content.append(text)
                elif elem.name in ['ul', 'ol']:
                    for li in elem.find_all('li'):
                        content.append(f"- {li.get_text(strip=True)}")
            
            # Stop if we reach the footer
            if text.startswith('PS -'):
                break
        
        text = '\n\n'.join(content)
        
        block = {
            "block_type": "article",
            "title": "Dorie Clark's Insights",
            "body_text": text,
            "image_url": "",
            "link_url": "",
        }
        
        processed_block = process_content_block(block)
        if processed_block['block_type'] != 'removed':
            # Ensure categories are assigned even if the utility function didn't do it
            if not processed_block.get('categories'):
                processed_block['categories'] = determine_categories(processed_block)
            content_blocks.append(processed_block)
        
        logger.debug(f"Processed main content: {text[:200]}...")  # Log first 200 characters
    
    translate_content_blocks(content_blocks)
    return content_blocks

def translate_content_blocks(blocks):
    for block in blocks:
        try:
            title = block.get('title', '').strip()
            body = block.get('body_text', '').strip()
            
            if title and body:
                combined_text = f"{title}\n{body}"
                translated_text = cached_translate(combined_text)
                try:
                    translated_title, translated_body = translated_text.split('\n', 1)
                    block['translated_title'] = translated_title
                    block['translated_body_text'] = translated_body
                except ValueError:
                    logger.warning(f"Could not split translated text for block: {title[:30]}...")
                    block['translated_title'] = translated_text
                    block['translated_body_text'] = ''
            elif title:
                block['translated_title'] = cached_translate(title)
                block['translated_body_text'] = ''
            elif body:
                block['translated_title'] = ''
                block['translated_body_text'] = cached_translate(body)
            else:
                logger.warning(f"Empty content block found: {block}")
        except Exception as e:
            logger.error(f"Error translating block: {e}")
            block['translated_title'] = block.get('title', '')
            block['translated_body_text'] = block.get('body_text', '')

# No Flask app or route decorators in this file