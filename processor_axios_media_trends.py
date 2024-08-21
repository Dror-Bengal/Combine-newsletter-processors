from bs4 import BeautifulSoup
import re
from datetime import datetime
from translator import translate_text
import logging
import json
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
            "source_name": "Axios Media Trends",
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

def process_axios_media_trends(data):
    logger.debug("Starting to process Axios Media Trends email")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        if not is_axios_media_trends(metadata):
            logger.info("Email is not from Sara Fischer at Axios")
            return {"error": "Not an Axios Media Trends newsletter"}, 400
        
        output_json = create_base_output_structure(metadata)
        
        logger.debug(f"Content HTML length: {len(content_html)}")
        
        soup = BeautifulSoup(content_html, 'html.parser')
        logger.debug(f"BeautifulSoup object created. Number of tags: {len(soup.find_all())}")

        content_blocks = extract_content_blocks(soup)
        output_json['content']['content_blocks'] = content_blocks
        
        logger.debug(f"Number of content blocks extracted: {len(content_blocks)}")
        
        logger.debug(f"Processed output: {json.dumps(output_json, indent=2)}")
        return output_json, 200

    except Exception as e:
        logger.exception("Unexpected error in process_axios_media_trends")
        return {"error": str(e)}, 500

def is_axios_media_trends(metadata):
    sender = metadata.get('sender', '').lower()
    sender_name = metadata.get('Sender name', '').lower()
    subject = metadata.get('subject', '').lower()
    
    is_correct_sender = 'sara@axios.com' in sender
    is_correct_name = 'sara fischer' in sender_name
    is_axios_newsletter = 'axios' in subject
    
    logger.debug(f"Sender check: {is_correct_sender}, Name check: {is_correct_name}, Subject check: {is_axios_newsletter}")
    logger.debug(f"Full subject: {subject}")
    
    return is_correct_sender and is_correct_name and is_axios_newsletter

def extract_content_blocks(soup):
    content_blocks = []
    
    story_sections = soup.find_all('td', class_='post-text')
    
    for section in story_sections:
        headline = section.find_previous('span', class_='bodytext hed')
        headline_text = headline.text.strip() if headline else ""
        
        if "Axios Pro Reports" in headline_text or "Today's Media Trends" in headline_text:
            continue
        
        paragraphs = section.find_all('p')
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
        if not content.strip() and not headline_text.strip():
            continue
        
        links = section.find_all('a', href=True)
        link = links[0]['href'] if links else ""
        
        img = section.find('img')
        image_url = img['src'] if img else ""
        
        block = {
            "block_type": "article",
            "title": headline_text or "Untitled",  # Use "Untitled" if no title is found
            "body_text": content,
            "image_url": image_url,
            "link_url": link,
        }
        
        processed_block = process_content_block(block)
        if processed_block['block_type'] != 'removed':
            # Ensure categories are assigned even if the utility function didn't do it
            if not processed_block.get('categories'):
                processed_block['categories'] = determine_categories(processed_block)
            content_blocks.append(processed_block)
        logger.debug(f"Processed story: {headline_text[:50]}...")
    
    translate_content_blocks(content_blocks)
    return content_blocks

def translate_content_blocks(blocks):
    for block in blocks:
        try:
            title = block.get('title', '').strip()
            body = block.get('body_text', '').strip()
            
            if title:
                block['translated_title'] = cached_translate(title)
            else:
                block['translated_title'] = ''
            
            if body:
                block['translated_body_text'] = cached_translate(body)
            else:
                block['translated_body_text'] = ''
            
            logger.debug(f"Translated block - Title: {block['translated_title'][:30]}..., Body: {block['translated_body_text'][:30]}...")
        except Exception as e:
            logger.error(f"Error translating block: {e}")
            block['translated_title'] = block.get('title', '')
            block['translated_body_text'] = block.get('body_text', '')

# No Flask app or route decorators in this file