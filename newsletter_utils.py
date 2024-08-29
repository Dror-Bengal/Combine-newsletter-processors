import re
from typing import List, Dict
import json
import html2text
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load categories and advertising keywords from a JSON file
with open('newsletter_config.json', 'r') as config_file:
    config = json.load(config_file)
    CATEGORIES = config['categories']
    AD_KEYWORDS = config['ad_keywords']

logger.debug(f"Loaded categories: {CATEGORIES}")

def is_advertisement(content_block):
    text = content_block.get('body_text', '').lower()
    title = content_block.get('title', '').lower()

    # Check for exact matches of ad keywords
    for keyword in AD_KEYWORDS:
        if keyword.lower() in text or keyword.lower() in title:
            return True

    # Check for promotional language patterns
    promo_patterns = [
        r"\d+% off",
        r"sign up and get",
        r"how it's done:",
        r"answer a few questions",
        r"get matched",
        r"connect with .+ therapists?",
        r"helping millions",
        r"lead happier, healthier lives",
        r"in as little as \d+ hours",
    ]

    for pattern in promo_patterns:
        if re.search(pattern, text, re.IGNORECASE) or re.search(pattern, title, re.IGNORECASE):
            return True

    return False

def process_content_block(content_block: Dict) -> Dict:
    if is_advertisement(content_block):
        return None  # We'll filter out None values later

    processed_block = {
        "title": content_block.get('title', ''),
        "image_url": content_block.get('image_url', ''),
        "body_text": content_block.get('body_text', ''),
        "link": content_block.get('link_url', ''),
        "credit": content_block.get('credit', '')
    }

    return processed_block

def html_to_text(html_content: str) -> str:
    """Convert HTML content to plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    return h.handle(html_content)

# ... [keep any other utility functions that might be used elsewhere] ...