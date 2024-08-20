import json
from bs4 import BeautifulSoup
import re
import logging
from translator import translate_text
import html2text

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    logger.info("SpaCy model loaded successfully")
except ImportError:
    logger.warning("SpaCy not installed. Some features will be limited.")
    nlp = None
except OSError:
    logger.warning("SpaCy model not found. Some features will be limited.")
    nlp = None

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "No Mercy No Malice",
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
        "translation_info": {
            "translated_language": "he",
            "translation_method": "Google Translate API"
        }
    }

def process_email(data):
    logger.debug("Starting process_email function")
    try:
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

        content_blocks = extract_content_blocks(soup)
        output_json['content']['content_blocks'] = content_blocks
        
        logger.debug(f"Processed output: {json.dumps(output_json, indent=2)}")
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
            "block_type": "article",
            "title": enriched_data['main_point'][:100],  # Use the first 100 characters of the main point as the title
            "translated_title": translate_text(enriched_data['main_point'][:100]),
            "description": main_content[:200] + "..." if len(main_content) > 200 else main_content,
            "translated_description": translate_text(main_content[:200] + "..." if len(main_content) > 200 else main_content),
            "body_text": main_content,
            "translated_body_text": translated_content,
            "image_url": "",
            "link_url": "",
            "category": enriched_data['main_category'],
            "tags": enriched_data['tags']
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

def enrich_content(text):
    logger.debug("Starting content enrichment")
    
    result = {
        'tags': [],
        'main_point': "",
        'main_category': "General",
    }

    try:
        if nlp:
            doc = nlp(text)
            logger.debug(f"SpaCy processing completed. Document length: {len(doc)}")

            # Extract tags (entities)
            result['tags'] = [ent.text for ent in doc.ents]
            logger.debug(f"Extracted {len(result['tags'])} tags")

            # Generate main point (summary)
            sentences = list(doc.sents)
            result['main_point'] = str(sentences[0]) if sentences else text[:200]
            logger.debug(f"Generated main point of length: {len(result['main_point'])}")

            # Simple categorization based on common words
            categories = {
                "Business": ["business", "entrepreneur", "startup", "company"],
                "Technology": ["tech", "technology", "software", "digital"],
                "Finance": ["finance", "investment", "stock", "market"],
                "Culture": ["culture", "society", "people", "trend"]
            }
            
            word_set = set(token.text.lower() for token in doc)
            for category, keywords in categories.items():
                if any(keyword in word_set for keyword in keywords):
                    result['main_category'] = category
                    break
            
            logger.debug(f"Determined category: {result['main_category']}")
        else:
            # Fallback if SpaCy is not available
            words = text.split()
            result['main_point'] = ' '.join(words[:20]) + "..."
            result['tags'] = list(set(words[:10]))  # Use first 10 unique words as tags

    except Exception as e:
        logger.exception(f"Unexpected error in content enrichment: {str(e)}")

    return result

# No Flask app or route decorators in this file