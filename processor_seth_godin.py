import json
from bs4 import BeautifulSoup
from translator import translate_text
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_email(data):
    try:
        logger.debug("Starting to process Seth Godin's email")
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_block = extract_content_block(soup)
        
        output_json = {
            "content_blocks": [content_block]
        }
        
        logger.debug("Successfully processed Seth Godin's email")
        return output_json, 200

    except Exception as e:
        logger.exception("Unexpected error in process_email")
        return {"error": str(e)}, 500

def extract_content_block(soup):
    logger.debug("Extracting content block")
    # Extract main image (if any)
    main_image = soup.find('img', class_='c24')
    image_url = main_image['src'] if main_image else ""

    # Extract main content
    main_content = extract_main_content(soup)

    # Translate main content
    try:
        translated_content = translate_text(main_content)
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        translated_content = main_content  # Fallback to original content

    content_block = {
        "text": main_content,
        "image": image_url,
        "link": "",
        "scoring": 1,
        "enrichment_text": generate_enrichment_text(main_content),
        "main_category": "Newsletter",
        "sub_category": "Seth Godin's Blog",
        "social_trend": generate_social_trend(main_content),
        "translated_text": translated_content,
        "translated_description": ""  # No separate description for this content
    }

    return content_block

def extract_main_content(soup):
    logger.debug("Extracting main content")
    content_container = soup.find('div', class_='rssDesc')
    if not content_container:
        logger.warning("Content container not found")
        return ""

    # Extract title
    title = content_container.find('h2')
    title_text = title.get_text(strip=True) if title else ""

    # Extract paragraphs
    paragraphs = content_container.find_all('p')
    content_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    main_content = f"{title_text}\n\n{content_text}"
    return main_content

def generate_enrichment_text(content):
    # This is a placeholder. Implement actual enrichment logic here.
    return content[:100] + "..."  # Return first 100 characters as a simple summary

def generate_social_trend(content):
    # This is a placeholder. Implement actual trend generation logic here.
    words = content.split()[:2]
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#SethGodin"

# No Flask app or route decorators in this file