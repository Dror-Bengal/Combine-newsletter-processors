import re
from typing import List, Dict
import json
from collections import Counter
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
    
    # Score based on category relevance
    categories = determine_categories(content_block)
    score += len(categories) * 5  # 5 points per relevant category
    
    # Score for presence of data (numbers, percentages)
    data_pattern = r'\d+%|\d+\.\d+|\b\d+\b'
    data_matches = re.findall(data_pattern, content_block.get('body_text', ''))
    score += min(len(data_matches) * 2, 10)  # Max 10 points for data
    
    # Score for presence of quotes
    quote_pattern = r'"[^"]*"'
    quote_matches = re.findall(quote_pattern, content_block.get('body_text', ''))
    score += min(len(quote_matches) * 3, 15)  # Max 15 points for quotes
    
    # Normalize score to 0-100 range
    return min(score, 100)

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

def determine_categories(content_block: Dict, num_categories=3) -> List[str]:
    text = content_block.get('body_text', '').lower()
    title = content_block.get('title', '').lower()
    
    # Combine title and body text
    full_text = f"{title} {text}"
    
    logger.debug(f"Determining categories for text: {full_text[:100]}...")  # Log first 100 characters
    
    # Count occurrences of each category in the text
    category_counts = Counter()
    for category in CATEGORIES:
        count = sum(1 for word in category.lower().split() if word in full_text)
        if count > 0:
            category_counts[category] = count
    
    logger.debug(f"Category counts: {dict(category_counts)}")
    
    # Get the top categories
    top_categories = [category for category, _ in category_counts.most_common(num_categories)]
    
    logger.debug(f"Top categories: {top_categories}")
    
    return top_categories

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

def clean_text(text: str) -> str:
    """Remove special characters and extra whitespace from text."""
    # Remove special characters
    text = re.sub(r'[^\w\s]', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def summarize_text(text: str, sentence_count: int = 3) -> str:
    """Create a simple summary of the text by extracting key sentences."""
    sentences = text.split('.')
    word_counts = [len(sentence.split()) for sentence in sentences]
    avg_length = sum(word_counts) / len(word_counts)
    
    important_sentences = []
    for sentence in sentences:
        if len(sentence.split()) >= avg_length:
            important_sentences.append(sentence)
    
    summary = '. '.join(important_sentences[:sentence_count]) + '.'
    return summary

def get_word_count(text: str) -> int:
    """Count the number of words in the text."""
    return len(text.split())

def get_readability_score(text: str) -> float:
    """Calculate a simple readability score based on sentence length and word complexity."""
    sentences = text.split('.')
    words = text.split()
    avg_sentence_length = len(words) / len(sentences)
    complex_words = len([word for word in words if len(word) > 6])
    readability_score = (0.39 * avg_sentence_length) + (11.8 * complex_words / len(words)) - 15.59
    return round(readability_score, 2)

def process_newsletter(content_blocks: List[Dict]) -> Dict:
    processed_blocks = [process_content_block(block) for block in content_blocks]
    non_ad_blocks = [block for block in processed_blocks if block is not None]

    return {
        "content_blocks": non_ad_blocks
    }
    
    return {
        "content_blocks": non_ad_blocks,
        "overall_stats": overall_stats
    }

def html_to_text(html_content: str) -> str:
    """Convert HTML content to plain text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    return h.handle(html_content)