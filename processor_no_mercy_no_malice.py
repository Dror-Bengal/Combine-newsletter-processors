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

logging.basicConfig(level=logging.DEBUG)
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
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
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

    # Adjust these selectors based on the actual structure of the Scout Galway newsletter
    main_content = soup.find('div', class_='main-content')
    if not main_content:
        logger.warning("Main content container not found")
        return content_blocks

    articles = main_content.find_all('article')
    for idx, article in enumerate(articles, start=1):
        title = article.find('h2')
        link = article.find('a', href=True)
        image = article.find('img', src=True)
        description = article.find('p', class_='description')

        if title and link:
            content = {
                "text": title.text.strip(),
                "link": link['href'],
                "image": image['src'] if image else "",
                "description": description.text.strip() if description else "",
                "scoring": idx  # Simple scoring based on order
            }
            
            enriched_data = enrich_content(content['text'] + " " + content['description'])
            content.update(enriched_data)
            
            # Translate content
            content['translated_text'] = translate_text(content['text'])
            content['translated_description'] = translate_text(content['description'])
            
            content_blocks.append(content)

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

# You might need additional helper functions depending on the complexity of the Scout Galway newsletter

if __name__ == "__main__":
    # You can add some test code here to run the processor independently
    pass