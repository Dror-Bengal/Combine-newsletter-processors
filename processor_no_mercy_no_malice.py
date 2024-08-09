import logging
from bs4 import BeautifulSoup
import requests
from textblob import TextBlob
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from translator import translate_text
import re

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("SpaCy model loaded successfully")
except OSError:
    logger.error("SpaCy model not found. Please download it using: python -m spacy download en_core_web_sm")
    nlp = None

# Simple category classifier
category_classifier = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('clf', MultinomialNB()),
])

# Train the classifier with some sample data (you should use more data in practice)
sample_texts = ["Galway wins hurling championship", "New tech startup in Galway", "Cultural festival in Galway"]
sample_categories = ["Sports", "Technology", "Culture"]
category_classifier.fit(sample_texts, sample_categories)

def process_email(data):
    logger.debug("Starting process_email function for Scout Galway")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        logger.debug(f"Received metadata: {metadata}")
        logger.debug(f"HTML content length: {len(content_html)}")
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
        if not content_blocks:
            logger.warning("No content blocks extracted")
        
        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }
        
        logger.debug(f"Processed output: {output_json}")
        return output_json, 200

    except Exception as e:
        logger.exception("Unexpected error in process_email")
        return {"error": str(e)}, 500

def extract_content_blocks(soup):
    logger.debug("Starting extract_content_blocks function")
    content_blocks = []

    # Log the entire HTML structure for debugging
    logger.debug(f"Full HTML content:\n{soup.prettify()}")

    # Try different possible selectors for the main content
    possible_selectors = [
        'div.main-content',
        'div.content',
        'div#main',
        'div.newsletter-content',
        'body'  # Fallback to the entire body if no specific container is found
    ]

    main_content = None
    for selector in possible_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            logger.debug(f"Found main content using selector: {selector}")
            break

    if not main_content:
        logger.warning("Main content container not found")
        return content_blocks

    # Try to find articles or content sections
    articles = main_content.find_all(['article', 'div', 'section'])
    logger.debug(f"Found {len(articles)} potential content sections")

    for idx, article in enumerate(articles, start=1):
        logger.debug(f"Processing content section {idx}")
        logger.debug(f"Content section HTML:\n{article.prettify()}")

        # Try different selectors for title, link, image, and description
        title = article.find(['h1', 'h2', 'h3', 'strong'])
        link = article.find('a', href=True)
        image = article.find('img', src=True)
        description = article.find(['p', 'div'], class_=['description', 'content', 'text'])

        if title and (link or description):
            content = {
                "text": title.text.strip(),
                "link": link['href'] if link else "",
                "image": image['src'] if image else "",
                "description": description.text.strip() if description else "",
                "scoring": idx
            }
            
            logger.debug(f"Extracted content: {content}")

            enriched_data = enrich_content(content['text'] + " " + content['description'])
            content.update(enriched_data)
            
            # Translate content
            content['translated_text'] = translate_text(content['text'])
            content['translated_description'] = translate_text(content['description'])
            
            content_blocks.append(content)
        else:
            logger.warning(f"Skipped content section {idx} due to missing title or content")

    logger.debug(f"Extracted {len(content_blocks)} content blocks")
    return content_blocks

def enrich_content(text):
    logger.debug("Starting content enrichment")
    
    result = {
        'tags': [],
        'main_point': "",
        'sentiment': 0,
        'main_category': "Newsletter",
        'sub_category': "General",
        'social_trend': "",
        'related_topics': []
    }

    try:
        if nlp is None:
            logger.error("SpaCy model not loaded. Cannot perform content enrichment.")
            return result

        doc = nlp(text)

        # Extract tags (entities)
        result['tags'] = [ent.text for ent in doc.ents]

        # Generate main point (summary)
        result['main_point'] = text[:200] + "..."  # Simple summary, first 200 characters

        # Sentiment analysis
        blob = TextBlob(text)
        result['sentiment'] = blob.sentiment.polarity

        # Categorization
        result['sub_category'] = category_classifier.predict([text])[0]

        # Social trend (simple example)
        words = re.findall(r'\w+', text.lower())
        result['social_trend'] = f"#{words[0]}{words[1].capitalize()}" if len(words) > 1 else "#ScoutGalway"

        # Related topics (based on noun chunks)
        result['related_topics'] = [chunk.text for chunk in doc.noun_chunks][:5]

    except Exception as e:
        logger.exception(f"Unexpected error in content enrichment: {str(e)}")

    return result

if __name__ == "__main__":
    # You can add some test code here to run the processor independently
    pass