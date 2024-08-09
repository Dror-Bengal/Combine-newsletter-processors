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
        
        return output_json, 200

    except Exception as e:
        logger.error(f"Error in process_email: {str(e)}")
        return {"error": str(e)}, 500

def extract_content_blocks(soup):
    content_blocks = []
    
    # Extract main content
    main_content = extract_main_content(soup)
    if main_content:
        content_blocks.append(main_content)
    
    # Extract bullet points
    bullet_points = extract_bullet_points(soup)
    if bullet_points:
        content_blocks.append(bullet_points)
    
    return content_blocks

def extract_main_content(soup):
    main_content = soup.find('div', class_='message-content')
    if main_content:
        # Find all paragraphs before the first image
        paragraphs = []
        for elem in main_content.find_all(['p', 'img'], recursive=False):
            if elem.name == 'img':
                break
            if elem.name == 'p':
                paragraphs.append(elem.get_text(strip=True))
        
        text = '\n\n'.join(paragraphs)
        translated_text = translate_text(text)
        
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

def extract_bullet_points(soup):
    bullet_list = soup.find('ul', class_='unordered_list')
    if bullet_list:
        bullet_points = bullet_list.find_all('li', class_='list_item')
        text = '\n'.join([point.get_text(strip=True) for point in bullet_points])
        translated_text = translate_text(text)
        
        return {
            "text": text,
            "translated_text": translated_text,
            "link": "",
            "image": "",
            "scoring": 2,
            "enrichment_text": "",
            "main_category": "Newsletter",
            "sub_category": "Key Points",
            "social_trend": ""
        }
    return None

# No Flask app or route decorators in this file