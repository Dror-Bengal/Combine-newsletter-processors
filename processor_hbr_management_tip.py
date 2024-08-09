import logging
from bs4 import BeautifulSoup
from translator import translate_text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_email(data):
    try:
        # Check if all required criteria are met
        if not meets_criteria(data):
            logger.info("Email does not meet the criteria for HBR Management Tip of the Day")
            return None, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_block = extract_content(soup)
        
        if content_block:
            output_json = {
                "metadata": metadata,
                "content_blocks": [content_block]
            }
            return output_json, 200
        else:
            return {"error": "Failed to extract content"}, 400

    except Exception as e:
        logger.error(f"Error processing HBR Management Tip email: {str(e)}")
        return {"error": str(e)}, 500

def meets_criteria(data):
    sender = data['metadata'].get('sender', '')
    subject = data['metadata'].get('subject', '')
    sender_name = data['metadata'].get('Sender name', '')

    return (
        sender == "emailteam@emails.hbr.org" and
        subject == "The Management Tip of the Day" and
        sender_name == "Harvard Business Review"
    )

def extract_content(soup):
    try:
        # Extract the main content
        main_content = soup.find('div', class_='rssDesc')
        if not main_content:
            logger.warning("Main content not found")
            return None

        # Extract title
        title = main_content.find('h1')
        title_text = title.get_text(strip=True) if title else ""

        # Extract the tip content
        tip_content = main_content.find('div', style=lambda value: value and 'font-family:Georgia,Times,\'Times New Roman\',serif' in value)
        tip_text = tip_content.get_text(strip=True) if tip_content else ""

        # Extract the source
        source = main_content.find('p', style=lambda value: value and 'font-family:Helvetica Neue,Helvetica,Arial,sans-serif' in value)
        source_text = source.get_text(strip=True) if source else ""

        # Translate content
        translated_title = translate_text(title_text)
        translated_tip = translate_text(tip_text)

        content_block = {
            "text": title_text,
            "description": tip_text,
            "translated_text": translated_title,
            "translated_description": translated_tip,
            "link": "",  # No specific link found in the example
            "image": "",  # No image found in the example
            "scoring": 1,
            "enrichment_text": source_text,
            "main_category": "Management Tip",
            "sub_category": determine_sub_category(title_text),
            "social_trend": generate_social_trend(title_text)
        }

        return content_block

    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return None

def determine_sub_category(text):
    # This is a simple example. You might want to implement more sophisticated categorization
    categories = {
        'Leadership': ['lead', 'manage', 'team'],
        'Communication': ['communicate', 'present', 'speak'],
        'Productivity': ['productive', 'efficiency', 'time management'],
        'Innovation': ['innovate', 'create', 'new ideas'],
        'Career Development': ['career', 'professional growth', 'skill']
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General Management"

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the title
    return f"#{''.join(words)}" if len(words) > 1 else "#ManagementTip"