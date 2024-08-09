import logging
from bs4 import BeautifulSoup
from translator import translate_text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }
        
        logger.debug(f"Extracted content blocks: {content_blocks}")
        return output_json, 200

    except Exception as e:
        logger.error(f"Error in process_email: {str(e)}")
        return {"error": str(e)}, 500

def extract_content_blocks(soup):
    content_blocks = []
    
    main_content = extract_main_content(soup)
    if main_content:
        content_blocks.append(main_content)
    
    return content_blocks

def extract_main_content(soup):
    main_content_div = soup.find('div', class_='message-content')
    if main_content_div:
        content = []
        for elem in main_content_div.find_all(['p', 'ul', 'ol']):
            if elem.name == 'p':
                content.append(elem.get_text(strip=True))
            elif elem.name in ['ul', 'ol']:
                for li in elem.find_all('li'):
                    content.append(f"- {li.get_text(strip=True)}")
            
            # Stop if we reach the sponsored content
            if '***' in elem.get_text():
                break
        
        text = '\n\n'.join(content)
        translated_text = translate_text(text)
        
        logger.debug(f"Extracted main content: {text[:200]}...")  # Log first 200 characters
        
        return {
            "text": text,
            "translated_text": translated_text,
            "link": "",
            "image": "",
            "scoring": 1,
            "enrichment_text": "",
            "main_category": "Newsletter",
            "sub_category": "Main Content",
            "social_trend": ""
        }
    return None

# No Flask app or route decorators in this file