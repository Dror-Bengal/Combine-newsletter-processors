import re
from typing import List, Dict
import json

# Load categories and advertising keywords from a JSON file
with open('newsletter_config.json', 'r') as config_file:
    config = json.load(config_file)
    CATEGORIES = config['categories']
    AD_KEYWORDS = config['ad_keywords']

def calculate_score(content_block: Dict) -> int:
    score = 0
    
    # Score based on content length
    text_length = len(content_block.get('body_text', ''))
    score += min(text_length // 20, 40)  # Max 40 points for length
    
    # Score for presence of image
    if content_block.get('image_url'):
        score += 10
    
    # Score for presence of link
    if content_block.get('link_url'):
        score += 5
    
    # Score based on category relevance (implement later)
    categories = determine_categories(content_block)
    score += len(categories) * 5  # 5 points per relevant category
    
    # Normalize score to 0-100 range
    return min(score, 100)

def is_advertisement(content_block: Dict) -> bool:
    text = content_block.get('body_text', '').lower()
    title = content_block.get('title', '').lower()
    
    for keyword in AD_KEYWORDS:
        if keyword.lower() in text or keyword.lower() in title:
            return True
    
    return False

def determine_categories(content_block: Dict) -> List[str]:
    text = content_block.get('body_text', '').lower()
    title = content_block.get('title', '').lower()
    
    relevant_categories = []
    for category, keywords in CATEGORIES.items():
        if any(keyword.lower() in text or keyword.lower() in title for keyword in keywords):
            relevant_categories.append(category)
    
    return relevant_categories[:3]  # Return top 3 categories

def process_content_block(content_block: Dict) -> Dict:
    if is_advertisement(content_block):
        return None  # Filter out advertisements
    
    content_block['score'] = calculate_score(content_block)
    content_block['categories'] = determine_categories(content_block)
    
    return content_block