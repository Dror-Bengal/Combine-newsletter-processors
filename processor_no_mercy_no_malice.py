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

        content_blocks = extract_content_blocks(soup)
        if content_blocks:
            output_json['content']['content_blocks'] = content_blocks
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

def extract_content_blocks(soup):
    logger.debug("Extracting content blocks")
    try:
        content_blocks = []
        main_content = soup.find('tr', id='content-blocks')
        
        if not main_content:
            logger.warning("Main content container not found")
            return None

        # Find all content sections
        content_sections = main_content.find_all('td', class_='dd')
        
        full_content = ""
        for section in content_sections:
            # Extract text from paragraphs and headers
            elements = section.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            section_content = "\n\n".join([elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)])
            full_content += section_content + "\n\n"

        # Remove any unwanted footer content
        full_content = re.sub(r'\nP\.S\..+', '', full_content, flags=re.DOTALL)
        full_content = re.sub(r'\nP\.P\.S\..+', '', full_content, flags=re.DOTALL)

        # Extract title (use the first non-empty line as title)
        title_match = re.search(r'^(.+)$', full_content, re.MULTILINE)
        title = title_match.group(1) if title_match else "No Mercy No Malice Insights"

        block = {
            "block_type": "article",
            "title": title[:100],  # Limit title to 100 characters
            "body_text": full_content.strip(),
            "image_url": "",
            "link_url": "",
        }
        
        processed_block = process_content_block(block)
        if processed_block['block_type'] != 'removed':
            processed_block['categories'] = determine_categories(processed_block)
            processed_block['translated_title'] = cached_translate(processed_block['title'])
            processed_block['translated_body_text'] = translate_long_text(processed_block['body_text'])
            processed_block['score'] = calculate_score(processed_block)
            content_blocks.append(processed_block)
        
        logger.debug(f"Extracted {len(content_blocks)} content blocks")
        return content_blocks

    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return None

def translate_long_text(text, max_chunk_size=5000):
    chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
    translated_chunks = [cached_translate(chunk) for chunk in chunks]
    return ' '.join(translated_chunks)

def calculate_score(block):
    score = 0
    
    # Score based on content length
    text_length = len(block.get('body_text', ''))
    score += min(text_length // 100, 50)  # Max 50 points for length
    
    # Score for presence of categories
    score += len(block.get('categories', [])) * 10  # 10 points per category
    
    # Normalize score to 0-100 range
    return min(score, 100)

# No Flask app or route decorators in this file