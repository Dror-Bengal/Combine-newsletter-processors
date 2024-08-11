import logging
from bs4 import BeautifulSoup
from translator import translate_text
import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Harvard Business Review Management Tip of the Day",
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
        if not meets_criteria(data):
            logger.info("Email does not meet the criteria for HBR Management Tip of the Day")
            return None, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        output_json = create_base_output_structure(metadata)
        
        soup = BeautifulSoup(content_html, 'html.parser')

        # Convert HTML to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False
        output_json['content']['main_content_text'] = h.handle(content_html)
        output_json['content']['translated_main_content_text'] = translate_text(output_json['content']['main_content_text'])

        content_block = extract_content(soup)
        
        if content_block:
            output_json['content']['content_blocks'] = [content_block]
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
        # Find the main content container
        main_content = soup.find('table', class_='row-content stack')
        
        if not main_content:
            logger.warning("Main content container not found")
            return None

        # Extract title
        title = main_content.find('h1')
        title_text = title.get_text(strip=True) if title else ""

        # Extract the tip content
        content_div = main_content.find('div', style=lambda s: s and 'font-family:Georgia,Times,\'Times New Roman\',serif' in s)
        tip_paragraphs = content_div.find_all('p') if content_div else []
        tip_text = "\n\n".join([p.get_text(strip=True) for p in tip_paragraphs])

        # Extract the source
        source_div = main_content.find('div', style=lambda s: s and 'font-family:Helvetica Neue,Helvetica,Arial,sans-serif' in s)
        source_text = source_div.get_text(strip=True) if source_div else ""

        content_block = {
            "block_type": "management_tip",
            "title": title_text,
            "translated_title": translate_text(title_text),
            "description": tip_text[:200] + "..." if len(tip_text) > 200 else tip_text,
            "translated_description": translate_text(tip_text[:200] + "..." if len(tip_text) > 200 else tip_text),
            "body_text": tip_text,
            "translated_body_text": translate_text(tip_text),
            "image_url": "",  # No image found in the content
            "link_url": "",  # No specific link found in the content
            "category": "Management Tip",
            "subcategory": determine_sub_category(title_text),
            "social_trend": generate_social_trend(title_text),
            "translated_social_trend": translate_text(generate_social_trend(title_text))
        }

        return content_block

    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return None

def determine_sub_category(text):
    categories = {
        'Leadership': ['lead', 'manage', 'team'],
        'Communication': ['communicate', 'present', 'speak', 'pitch'],
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

# No Flask app or route decorators in this file