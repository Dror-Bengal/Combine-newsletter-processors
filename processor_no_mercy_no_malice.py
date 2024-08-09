import json
from bs4 import BeautifulSoup
import re
import logging
from translator import translate_text
import spacy
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer as Summarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import datetime

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
sample_texts = ["The economy is growing", "New sports results", "Tech company launches product"]
sample_categories = ["Economics", "Sports", "Technology"]
category_classifier.fit(sample_texts, sample_categories)

def process_email(data):
    logger.debug("Starting process_email function")
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logger.error("Invalid JSON structure in input data")
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
        output_json = {
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

    main_content = extract_main_content(soup)
    if main_content:
        logger.debug(f"Main content extracted (length: {len(main_content)})")
        try:
            translated_content = translate_text(main_content)
            logger.debug("Main content translated successfully")
        except Exception as e:
            logger.error(f"Error translating main content: {str(e)}")
            translated_content = main_content  # Use original content if translation fails

        enriched_data = enrich_content(main_content)
        
        content_blocks.append({
            "text": main_content,
            "enrichment_text": enriched_data['main_point'],
            "image": "",
            "link": "",
            "scoring": enriched_data['score'],
            "main_category": enriched_data['main_category'],
            "sub_category": enriched_data['sub_category'],
            "social_trend": enriched_data['social_trend'],
            "translated_text": add_headlines(translated_content),
            "tags": enriched_data['tags'],
            "sentiment": enriched_data['sentiment'],
            "related_topics": enriched_data['related_topics'],
            "engagement_potential": enriched_data['engagement_potential'],
            "audience_targeting": enriched_data['audience_targeting'],
            "urgency": enriched_data['urgency'],
            "source_credibility": enriched_data['source_credibility']
        })

    logger.debug(f"Extracted {len(content_blocks)} content blocks")
    return content_blocks

def extract_main_content(soup):
    logger.debug("Starting extract_main_content function")
    content_container = soup.find('tr', id='content-blocks')
    if not content_container:
        logger.warning("Main content container not found")
        return ""

    paragraphs = content_container.find_all('p')
    main_content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    main_content = re.sub(r'\nP\.S\..+', '', main_content, flags=re.DOTALL)
    main_content = re.sub(r'\nP\.P\.S\..+', '', main_content, flags=re.DOTALL)

    logger.debug(f"Extracted main content (length: {len(main_content)})")
    return main_content

def add_headlines(text):
    lines = text.split('\n')
    result = []
    for line in lines:
        if len(line) <= 50 and not line.endswith('.'):
            result.append(f"<headline>{line}</headline>")
        else:
            result.append(line)
    return '\n'.join(result)

def enrich_content(text):
    logger.debug("Starting content enrichment")
    
    result = {
        'tags': [],
        'main_point': "",
        'sentiment': 0,
        'main_category': "Unknown",
        'sub_category': "General",
        'score': 0,
        'related_topics': [],
        'social_trend': "",
        'engagement_potential': 0,
        'audience_targeting': [],
        'urgency': 0,
        'source_credibility': 0
    }

    try:
        if nlp is None:
            logger.error("SpaCy model not loaded. Cannot perform content enrichment.")
            return result

        doc = nlp(text)
        logger.debug(f"SpaCy processing completed. Document length: {len(doc)}")

        # Extract tags (entities)
        result['tags'] = [ent.text for ent in doc.ents]
        logger.debug(f"Extracted {len(result['tags'])} tags")

        # Generate main point (summary)
        try:
            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            stemmer = Stemmer("english")
            summarizer = Summarizer(stemmer)
            summarizer.stop_words = get_stop_words("english")
            summary = summarizer(parser.document, 3)  # Summarize to 3 sentences
            result['main_point'] = " ".join([str(sentence) for sentence in summary])
            logger.debug(f"Generated summary of length: {len(result['main_point'])}")
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            result['main_point'] = text[:200] + "..."  # Fallback to first 200 characters

        # Sentiment Analysis
        blob = TextBlob(text)
        result['sentiment'] = blob.sentiment.polarity
        logger.debug(f"Calculated sentiment: {result['sentiment']}")

        # Categorization
        result['main_category'] = category_classifier.predict([text])[0]
        logger.debug(f"Predicted category: {result['main_category']}")

        # Scoring
        result['score'] = calculate_score(text, doc, result)
        logger.debug(f"Calculated score: {result['score']}")

        # Related topics (based on noun chunks)
        result['related_topics'] = [chunk.text for chunk in doc.noun_chunks][:5]
        logger.debug(f"Extracted {len(result['related_topics'])} related topics")

        # Social trend (simple example)
        words = text.split()[:2]
        result['social_trend'] = f"#{words[0]}{words[1]}" if len(words) > 1 else "#Trending"
        logger.debug(f"Generated social trend: {result['social_trend']}")

        # Engagement Potential
        result['engagement_potential'] = calculate_engagement_potential(text, doc, result)
        logger.debug(f"Calculated engagement potential: {result['engagement_potential']}")

        # Audience Targeting
        result['audience_targeting'] = determine_audience(text, doc, result)
        logger.debug(f"Determined audience targeting: {result['audience_targeting']}")

        # Urgency/Timeliness
        result['urgency'] = calculate_urgency(text, doc)
        logger.debug(f"Calculated urgency: {result['urgency']}")

        # Source Credibility
        result['source_credibility'] = estimate_source_credibility(text, doc)
        logger.debug(f"Estimated source credibility: {result['source_credibility']}")

    except Exception as e:
        logger.exception(f"Unexpected error in content enrichment: {str(e)}")

    return result

def calculate_score(text, doc, result):
    # Base score
    score = len(text) / 1000 + len(set(word.lower_ for word in doc)) / 100
    
    # Adjust based on sentiment (boost for strong sentiment)
    score += abs(result['sentiment']) * 2
    
    # Adjust based on engagement potential
    score += result['engagement_potential'] * 1.5
    
    # Adjust based on urgency
    score += result['urgency'] * 1.2
    
    # Adjust based on source credibility
    score += result['source_credibility'] * 1.1
    
    return min(score, 10)  # Cap the score at 10

def calculate_engagement_potential(text, doc, result):
    engagement = 0
    
    # Check for question marks (indicates potential for interaction)
    engagement += text.count('?') * 0.5
    
    # Check for exclamation marks (indicates excitement)
    engagement += text.count('!') * 0.3
    
    # Check for presence of common engaging words
    engaging_words = ['you', 'discover', 'amazing', 'shocking', 'unbelievable', 'must-see']
    engagement += sum(1 for word in doc if word.text.lower() in engaging_words) * 0.4
    
    # Consider sentiment (both positive and negative can be engaging)
    engagement += abs(result['sentiment']) * 2
    
    return min(engagement, 5)  # Cap at 5

def determine_audience(text, doc, result):
    audiences = []
    
    # Check for specific keywords related to different audiences
    if any(word in text.lower() for word in ['business', 'entrepreneur', 'startup']):
        audiences.append('Business Professionals')
    if any(word in text.lower() for word in ['tech', 'technology', 'software', 'hardware']):
        audiences.append('Tech Enthusiasts')
    if any(word in text.lower() for word in ['finance', 'investment', 'stock market']):
        audiences.append('Finance Professionals')
    if any(word in text.lower() for word in ['health', 'wellness', 'fitness']):
        audiences.append('Health-Conscious Individuals')
    
    # If no specific audience is determined, add a general one
    if not audiences:
        audiences.append('General Public')
    
    return audiences

def calculate_urgency(text, doc):
    urgency = 0
    
    # Check for time-related words
    time_words = ['now', 'today', 'immediately', 'urgent', 'breaking']
    urgency += sum(1 for word in doc if word.text.lower() in time_words) * 0.5
    
    # Check for future dates
    current_year = datetime.datetime.now().year
    for ent in doc.ents:
        if ent.label_ == 'DATE':
            try:
                date = datetime.datetime.strptime(ent.text, "%Y-%m-%d")
                if current_year <= date.year <= current_year + 1:
                    urgency += 1
            except ValueError:
                pass  # If date parsing fails, just continue
    
    return min(urgency, 5)  # Cap at 5

def estimate_source_credibility(text, doc):
    credibility = 3  # Start with a neutral score
    
    # Check for presence of credible sources
    credible_sources = ['study', 'research', 'survey', 'expert', 'official']
    credibility += sum(0.5 for word in doc if word.text.lower() in credible_sources)
    
    # Check for presence of questionable language
    questionable_words = ['rumor', 'unconfirmed', 'allegedly']
    credibility -= sum(0.5 for word in doc if word.text.lower() in questionable_words)
    
    return max(min(credibility, 5), 1)  # Ensure the score is between 1 and 5

# No Flask app or route decorators in this file