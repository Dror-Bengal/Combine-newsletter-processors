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
    
    # Extract sponsor content
    sponsor_content = extract_sponsor_content(soup)
    if sponsor_content:
        content_blocks.append(sponsor_content)
    
    # Extract postscripts
    postscripts = extract_postscripts(soup)
    content_blocks.extend(postscripts)
    
    return content_blocks

def extract_main_content(soup):
    main_content = soup.find('div', class_='message-content')
    if main_content:
        paragraphs = main_content.find_all('p', recursive=False)
        text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs])
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

def extract_sponsor_content(soup):
    sponsor_section = soup.find('div', style=lambda value: value and 'padding-bottom:10px' in value)
    if sponsor_section:
        text = sponsor_section.get_text(strip=True)
        translated_text = translate_text(text)
        image = sponsor_section.find('img')
        image_url = image['src'] if image else ""
        
        return {
            "text": text,
            "translated_text": translated_text,
            "link": "",
            "image": image_url,
            "scoring": 2,
            "enrichment_text": "",
            "main_category": "Newsletter",
            "sub_category": "Sponsor Content",
            "social_trend": ""
        }
    return None

def extract_postscripts(soup):
    postscripts = []
    ps_sections = soup.find_all('div', style=lambda value: value and 'padding-bottom:10px' in value)
    
    for i, ps in enumerate(ps_sections[1:], start=3):  # Skip the first one as it's likely the sponsor content
        text = ps.get_text(strip=True)
        translated_text = translate_text(text)
        
        postscripts.append({
            "text": text,
            "translated_text": translated_text,
            "link": "",
            "image": "",
            "scoring": i,
            "enrichment_text": "",
            "main_category": "Newsletter",
            "sub_category": f"Postscript {i-2}",
            "social_trend": ""
        })
    
    return postscripts

# No Flask app or route decorators in this file