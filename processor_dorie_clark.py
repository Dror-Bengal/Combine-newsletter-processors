import logging
from bs4 import BeautifulSoup
from translator import translate_text
import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Dorie Clark Newsletter",
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
        "additional_info": {
            "attachments": [],
            "engagement_metrics": {}
        },
        "translation_info": {
            "translated_language": "he",
            "translation_method": "Google Translate API"
        }
    }

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
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
        
        logger.debug(f"Extracted content blocks: {len(content_blocks)}")
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
        in_ad_section = False
        ad_counter = 0
        
        for elem in main_content_div.find_all(['p', 'ul', 'ol', 'h2']):
            text = elem.get_text(strip=True)
            
            if "***" in text:
                ad_counter += 1
                in_ad_section = ad_counter % 2 != 0  # Toggle ad section on odd counts
                continue
            
            if not in_ad_section:
                if elem.name == 'p':
                    content.append(text)
                elif elem.name in ['ul', 'ol']:
                    for li in elem.find_all('li'):
                        content.append(f"- {li.get_text(strip=True)}")
            
            # Stop if we reach the footer
            if text.startswith('PS -'):
                break
        
        text = '\n\n'.join(content)
        
        logger.debug(f"Extracted main content: {text[:200]}...")  # Log first 200 characters
        
        return {
            "block_type": "newsletter_content",
            "title": "Dorie Clark's Insights",  # You might want to extract a more specific title if available
            "translated_title": translate_text("Dorie Clark's Insights"),
            "description": text[:200] + "..." if len(text) > 200 else text,
            "translated_description": translate_text(text[:200] + "..." if len(text) > 200 else text),
            "body_text": text,
            "translated_body_text": translate_text(text),
            "image_url": "",
            "link_url": "",
            "category": "Newsletter",
            "subcategory": determine_subcategory(text),
            "social_trend": generate_social_trend(text),
            "translated_social_trend": translate_text(generate_social_trend(text))
        }
    return None

def determine_subcategory(text):
    categories = {
        'Career Advice': ['career', 'job', 'work'],
        'Personal Branding': ['brand', 'personal brand', 'reputation'],
        'Leadership': ['lead', 'leadership', 'manage'],
        'Entrepreneurship': ['entrepreneur', 'startup', 'business'],
        'Networking': ['network', 'connection', 'relationship'],
        'Productivity': ['productivity', 'efficiency', 'time management']
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General Insights"

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the content
    return f"#{''.join(words)}" if len(words) > 1 else "#DorieClarkInsights"

# No Flask app or route decorators in this file