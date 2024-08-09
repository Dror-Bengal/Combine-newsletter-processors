import logging
from bs4 import BeautifulSoup
from translator import translate_text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_email(data):
    try:
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
        # Find the main content box (assuming it's the first table after "Today's Tip")
        main_content = soup.find('td', string='Today\'s Tip').find_next('table')
        
        if not main_content:
            logger.warning("Main content not found")
            return None

        # Extract title
        title = main_content.find('h1')
        title_text = title.get_text(strip=True) if title else ""

        # Extract the tip content (all p tags within the main content)
        tip_paragraphs = main_content.find_all('p')
        tip_text = "\n\n".join([p.get_text(strip=True) for p in tip_paragraphs if p.get_text(strip=True)])

        # Extract the source (last p tag)
        source = tip_paragraphs[-1] if tip_paragraphs else None
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
            "image": "",  # No image found in the content
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