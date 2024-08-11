from bs4 import BeautifulSoup
import re
from datetime import datetime
from translator import translate_text
import logging
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_axios_media_trends(data):
    logger.debug("Starting to process Axios Media Trends email")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        # Check if the email is from Sara Fischer at Axios
        if not is_axios_media_trends(metadata):
            logger.info("Email is not from Sara Fischer at Axios")
            return {"error": "Not an Axios Media Trends newsletter"}, 400
        
        logger.debug(f"Content HTML length: {len(content_html)}")
        
        soup = BeautifulSoup(content_html, 'html.parser')
        logger.debug(f"BeautifulSoup object created. Number of tags: {len(soup.find_all())}")

        content_blocks = extract_content_blocks(soup)
        
        logger.debug(f"Number of content blocks extracted: {len(content_blocks)}")
        
        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }
        
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
    is_media_trends = 'media trends' in subject
    
    logger.debug(f"Sender check: {is_correct_sender}, Name check: {is_correct_name}, Subject check: {is_media_trends}")
    
    return is_correct_sender and is_correct_name and is_media_trends

def extract_content_blocks(soup):
    content_blocks = []
    
    # Find all story sections
    story_sections = soup.find_all('td', class_='post-text')
    
    for section in story_sections:
        # Extract headline
        headline = section.find_previous('span', class_='bodytext hed')
        headline_text = headline.text.strip() if headline else ""
        
        # Skip sponsored content and the introductory section
        if "Axios Pro Reports" in headline_text or "Today's Media Trends" in headline_text:
            continue
        
        # Extract content
        paragraphs = section.find_all('p')
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
        # Skip if content is empty after stripping
        if not content.strip():
            continue
        
        # Extract links
        links = section.find_all('a', href=True)
        link = links[0]['href'] if links else ""
        
        # Extract image (if any)
        img = section.find('img')
        image_url = img['src'] if img else ""
        
        block = {
            "text": headline_text,
            "translated_text": translate_text(headline_text),
            "description": content,
            "translated_description": translate_text(content),
            "image": image_url,
            "link": link,
            "scoring": len(content_blocks) + 1,  # Update scoring to be consecutive
            "main_category": "Newsletter",
            "sub_category": determine_sub_category(headline_text),
            "social_trend": generate_social_trend(headline_text)
        }
        
        content_blocks.append(block)
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