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

def extract_content_blocks(soup):
    content_blocks = []
    
    # Find all story sections
    story_sections = soup.find_all('td', class_='post-text')
    
    for idx, section in enumerate(story_sections, start=1):
        # Extract headline
        headline = section.find('strong')
        headline_text = headline.text.strip() if headline else ""
        
        # Extract content
        paragraphs = section.find_all('p')
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
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
            "scoring": idx,
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

# This function is not used in the current implementation but could be useful for future enhancements
def extract_date(soup):
    date_string = soup.find('span', string=re.compile(r'\w+, \w+ \d{2}, \d{4}'))
    if date_string:
        return datetime.strptime(date_string.text.strip(), '%A, %B %d, %Y')
    return None