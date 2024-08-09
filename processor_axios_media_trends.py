from bs4 import BeautifulSoup
import re
from datetime import datetime
from translator import translate_text
import logging

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
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }
        
        logger.debug(f"Processed output: {output_json}")
        return output_json, 200

    except Exception as e:
        logger.exception("Unexpected error in process_axios_media_trends")
        return {"error": str(e)}, 500

def extract_content_blocks(soup):
    content_blocks = []
    main_stories = soup.find_all('tr', class_='post-text')
    
    for idx, story in enumerate(main_stories, start=1):
        block = process_story(story, idx)
        if block:
            content_blocks.append(block)
    
    logger.debug(f"Extracted {len(content_blocks)} content blocks")
    return content_blocks

def process_story(story, score):
    headline = story.find_previous('span', class_='bodytext hed')
    headline_text = headline.text.strip() if headline else ""
    
    image = story.find_previous('img')
    image_url = image['src'] if image else ""
    
    content = story.get_text(strip=True)
    
    link = story.find('a', href=True)
    link_url = link['href'] if link else ""
    
    block = {
        "text": headline_text,
        "translated_text": translate_text(headline_text),
        "description": content,
        "translated_description": translate_text(content),
        "image": image_url,
        "link": link_url,
        "scoring": score,
        "main_category": "Newsletter",
        "sub_category": determine_sub_category(headline_text),
        "social_trend": generate_social_trend(headline_text)
    }
    
    logger.debug(f"Processed story: {headline_text}")
    return block

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

def extract_date(soup):
    date_string = soup.find('span', string=re.compile(r'\w+, \w+ \d{2}, \d{4}'))
    if date_string:
        return datetime.strptime(date_string.text.strip(), '%A, %B %d, %Y')
    return None