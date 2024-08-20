import re
from typing import List, Dict
import json
from textblob import TextBlob

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    SPACY_AVAILABLE = False
    print("SpaCy model not available. Falling back to simpler implementation.")

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

def is_advertisement(content_block: Dict) -> bool:
    text = content_block.get('body_text', '').lower()
    title = content_block.get('title', '').lower()
    
    # Check for exact matches of ad keywords
    for keyword in AD_KEYWORDS:
        if keyword.lower() in text or keyword.lower() in title:
            return True
    
    # Check for promotional language
    promo_phrases = ['sign up', 'get % off', 'limited time offer', 'click here', 'special offer']
    if any(phrase in text for phrase in promo_phrases):
        return True
    
    return False

def determine_categories(content_block: Dict) -> List[str]:
    text = content_block.get('body_text', '').lower()
    title = content_block.get('title', '').lower()
    
    relevant_categories = []
    for category, keywords in CATEGORIES.items():
        category_score = sum(1 for keyword in keywords if keyword.lower() in text or keyword.lower() in title)
        if category_score > 0:
            relevant_categories.append((category, category_score))
    
    # Sort categories by relevance score and return top 3
    return [cat for cat, score in sorted(relevant_categories, key=lambda x: x[1], reverse=True)[:3]]

def analyze_sentiment(text: str) -> str:
    blob = TextBlob(text)
    sentiment_score = blob.sentiment.polarity
    if sentiment_score > 0.1:
        return "positive"
    elif sentiment_score < -0.1:
        return "negative"
    else:
        return "neutral"

def extract_entities(text: str) -> Dict[str, List[str]]:
    if SPACY_AVAILABLE:
        doc = nlp(text)
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "events": []
        }
        
        for ent in doc.ents:
            if ent.label_ == "PERSON" and len(ent.text.split()) > 1:  # Ensure full names
                entities["persons"].append(ent.text)
            elif ent.label_ == "ORG":
                entities["organizations"].append(ent.text)
            elif ent.label_ == "GPE":
                entities["locations"].append(ent.text)
            elif ent.label_ == "EVENT":
                entities["events"].append(ent.text)
        
        return {k: list(set(v)) for k, v in entities.items()}  # Remove duplicates
    else:
        # Simple fallback using regex
        entities = {
            "persons": list(set(re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text))),
            "organizations": [],
            "locations": [],
            "events": []
        }
        return entities

def process_content_block(content_block: Dict) -> Dict:
    if is_advertisement(content_block):
        return {
            "block_type": "removed",
            "reason": "Content block removed due to advertisement content"
        }
    
    processed_block = {
        "block_type": content_block.get('block_type', 'article'),
        "title": content_block.get('title', ''),
        "body_text": content_block.get('body_text', ''),
        "translated_body_text": content_block.get('translated_body_text', ''),
        "image_url": content_block.get('image_url', ''),
        "link_url": content_block.get('link_url', ''),
        "score": calculate_score(content_block),
        "categories": determine_categories(content_block),
        "sentiment": analyze_sentiment(content_block.get('body_text', '')),
        "entities": extract_entities(content_block.get('body_text', ''))
    }
    
    return processed_block

# Additional utility functions

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
    """Process the entire newsletter, including overall statistics."""
    processed_blocks = [process_content_block(block) for block in content_blocks]
    non_ad_blocks = [block for block in processed_blocks if block['block_type'] != 'removed']
    
    overall_stats = {
        "total_blocks": len(content_blocks),
        "non_ad_blocks": len(non_ad_blocks),
        "average_score": sum(block['score'] for block in non_ad_blocks) / len(non_ad_blocks) if non_ad_blocks else 0,
        "total_word_count": sum(get_word_count(block['body_text']) for block in non_ad_blocks),
        "overall_sentiment": analyze_sentiment(' '.join(block['body_text'] for block in non_ad_blocks))
    }
    
    return {
        "content_blocks": non_ad_blocks,
        "overall_stats": overall_stats
    }