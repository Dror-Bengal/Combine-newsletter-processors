import json
from bs4 import BeautifulSoup
import re
import logging
from translator import translate_text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

    # Extract main content
    main_content = extract_main_content(soup)
    if main_content:
        logger.debug(f"Main content extracted (length: {len(main_content)})")
        try:
            translated_content = translate_text(main_content)
            logger.debug("Main content translated successfully")
        except Exception as e:
            logger.error(f"Error translating main content: {str(e)}")
            translated_content = main_content  # Use original content if translation fails

        content_blocks.append({
            "enrichment_text": main_content,
            "image": "",
            "link": "",
            "scoring": 1,
            "main_category": "Newsletter",
            "sub_category": "Main Content",
            "social_trend": generate_social_trend(main_content),
            "translated_text": add_headlines(translated_content)
        })

    logger.debug(f"Extracted {len(content_blocks)} content blocks")
    return content_blocks

def extract_main_content(soup):
    logger.debug("Starting extract_main_content function")
    # Find the main content container
    content_container = soup.find('tr', id='content-blocks')
    if not content_container:
        logger.warning("Main content container not found")
        return ""

    # Extract all text from paragraphs within the content container
    paragraphs = content_container.find_all('p')
    main_content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

    # Remove P.S. and P.P.S. sections
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

def generate_social_trend(text):
    # This is a simple example. You might want to implement a more sophisticated method.
    words = text.split()[:2]  # Use first two words of the content
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#NoMercyNoMalice"

# No Flask app or route decorators in this file