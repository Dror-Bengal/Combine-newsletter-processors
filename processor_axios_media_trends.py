from bs4 import BeautifulSoup
import re
from datetime import datetime
from translator import translate_text
import logging
import json
import html2text
from newsletter_utils import process_content_block  # Add this new import

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Axios Media Trends",
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

        h = html2text.HTML2Text()
        h.ignore_links = False
        output_json['content']['main_content_text'] = h.handle(content_html)
        output_json['content']['translated_main_content_text'] = translate_text(output_json['content']['main_content_text'])

        content_blocks = extract_content_blocks(soup)
        processed_blocks = [block for block in content_blocks if block is not None]
        output_json['content']['content_blocks'] = processed_blocks
        
        logger.debug(f"Number of content blocks extracted: {len(processed_blocks)}")
        
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
        
        if not content.strip():
            continue
        
        links = section.find_all('a', href=True)
        link = links[0]['href'] if links else ""
        
        img = section.find('img')
        image_url = img['src'] if img else ""
        
        block = {
            "block_type": "article",
            "title": headline_text,
            "translated_title": translate_text(headline_text),
            "description": content[:200] + "..." if len(content) > 200 else content,
            "translated_description": translate_text(content[:200] + "..." if len(content) > 200 else content),
            "body_text": content,
            "translated_body_text": translate_text(content),
            "image_url": image_url,
            "link_url": link,
        }
        
        processed_block = process_content_block(block)
        if processed_block:
            content_blocks.append(processed_block)
        logger.debug(f"Processed story: {headline_text}")
    
    return content_blocks

def determine_sub_category(text):
    categories = {
        'AI': ['AI', 'artificial intelligence', 'machine learning'],
        'Media': ['media', 'streaming', 'broadcast', 'publishing'],
        'Technology': ['tech', 'software', 'hardware', 'digital'],
        'Business': ['business', 'company', 'industry', 'market'],
        'Advertising': ['ad', 'advertising', 'marketing'],
        'Social Media': ['social media', 'platform', 'network'],
        'Politics': ['politics', 'election', 'campaign'],
        'Entertainment': ['entertainment', 'Hollywood', 'streaming']
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

def generate_social_trend(text):
    words = text.split()[:2]
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#AxiosMediaTrends"

# No Flask app or route decorators in this file