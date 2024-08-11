import json
from bs4 import BeautifulSoup
from translator import translate_text
import logging
import html2text

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Seth Godin's Blog",
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

def process_email(data):
    try:
        logger.debug("Starting to process Seth Godin's email")
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        output_json = create_base_output_structure(metadata)
        
        soup = BeautifulSoup(content_html, 'html.parser')

        # Convert HTML to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False
        output_json['content']['main_content_text'] = h.handle(content_html)
        output_json['content']['translated_main_content_text'] = translate_text(output_json['content']['main_content_text'])

        content_block = extract_content_block(soup)
        output_json['content']['content_blocks'] = [content_block]
        
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

    # Extract headline and main content
    headline, main_content = extract_main_content(soup)

    content_block = {
        "block_type": "blog_post",
        "title": headline,
        "translated_title": translate_text(headline),
        "description": main_content[:200] + "..." if len(main_content) > 200 else main_content,
        "translated_description": translate_text(main_content[:200] + "..." if len(main_content) > 200 else main_content),
        "body_text": main_content,
        "translated_body_text": translate_text(main_content),
        "image_url": image_url,
        "link_url": "",  # Seth's emails typically don't include links to the full post
        "category": "Seth Godin's Blog",
        "subcategory": determine_sub_category(headline, main_content),
        "social_trend": generate_social_trend(headline),
        "translated_social_trend": translate_text(generate_social_trend(headline))
    }

    return content_block

def extract_main_content(soup):
    logger.debug("Extracting main content")
    content_container = soup.find('div', class_='rssDesc')
    if not content_container:
        logger.warning("Content container not found")
        return "", ""

    # Extract headline
    headline = content_container.find('h2')
    headline_text = headline.get_text(strip=True) if headline else ""

    # Extract paragraphs
    paragraphs = content_container.find_all('p')
    content_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    return headline_text, content_text

def determine_sub_category(headline, content):
    # This is a simple example. You might want to implement a more sophisticated categorization system.
    keywords = {
        'Marketing': ['marketing', 'brand', 'advertising'],
        'Leadership': ['leader', 'management', 'organization'],
        'Innovation': ['innovation', 'change', 'creativity'],
        'Personal Development': ['growth', 'learning', 'skill'],
        'Business Strategy': ['strategy', 'business', 'market']
    }
    
    combined_text = (headline + " " + content).lower()
    for category, words in keywords.items():
        if any(word in combined_text for word in words):
            return category
    return "General Insights"

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the headline
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#SethGodinInsight"

# No Flask app or route decorators in this file