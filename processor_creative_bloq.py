from bs4 import BeautifulSoup
import logging
import re
from translator import translate_text
import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Creative Bloq",
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
    logger.debug(f"Received request data: {data}")
    try:
        if 'metadata' not in data or 'content' not in data['metadata']:
            raise KeyError("Missing 'content' key in the 'metadata' section of the JSON payload")

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        output_json = create_base_output_structure(metadata)

        # Convert HTML to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False
        output_json['content']['main_content_text'] = h.handle(content_html)
        output_json['content']['translated_main_content_text'] = translate_text(output_json['content']['main_content_text'])

        # Extract stories from the HTML content
        content_blocks = extract_stories(content_html)
        output_json['content']['content_blocks'] = content_blocks
        
        logger.debug(f"Final output JSON: {output_json}")
        
        return output_json, 200
    except KeyError as e:
        logger.error(f"KeyError: {str(e)}")
        return {"error": str(e)}, 400
    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        return {"error": str(e)}, 400

def extract_stories(content):
    stories = []
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find all content blocks
    content_blocks = soup.find_all('table', class_='name-59')
    
    score = 1  # Initialize score to 1
    
    for block in content_blocks:
        # Find the section header
        section_header = block.find('td', class_='standard_section_header')
        if section_header:
            main_category = section_header.text.strip()
        else:
            main_category = "Newsletter"

        # Find all story blocks within this section
        story_blocks = block.find_all('table', class_='name-60')
        
        for story in story_blocks:
            story_data = {
                "block_type": "article",
                "scoring": score
            }
            
            # Extract headline
            headline = story.find('div', attrs={'data-testid': 'copy_headline'})
            if headline:
                story_data['title'] = headline.text.strip()
                story_data['translated_title'] = translate_text(story_data['title'])
            
            # Extract additional text
            additional_text = story.find('div', class_='name-100')
            if additional_text:
                story_data['description'] = additional_text.text.strip()
                story_data['translated_description'] = translate_text(story_data['description'])
            
            # Extract link
            link = story.find('a', attrs={'data-testid': 'cta_link'})
            if link:
                story_data['link_url'] = link['href']
            
            # Extract image
            img = story.find('img', class_='scale_full_width')
            if img:
                story_data['image_url'] = img['src']
            
            # Add other required fields
            story_data['body_text'] = story_data.get('description', '')
            story_data['translated_body_text'] = story_data.get('translated_description', '')
            story_data['category'] = main_category
            story_data['subcategory'] = determine_sub_category(story_data.get('title', ''))
            story_data['social_trend'] = generate_social_trend(story_data.get('title', ''))
            story_data['translated_social_trend'] = translate_text(story_data['social_trend'])
            
            if story_data.get('title') and (story_data.get('image_url') or story_data.get('link_url')):
                stories.append(story_data)
                score += 1  # Increment score for next item
    
    return stories

def determine_sub_category(text):
    categories = {
        'News': ['news', 'latest'],
        'Reviews': ['review', 'tested'],
        'Tutorials': ['how to', 'guide', 'tutorial'],
        'Features': ['feature', 'insight'],
        'Inspiration': ['inspiration', 'creative'],
        'Buying Guides': ['best', 'top', 'buy'],
        'Tech News': ['tech', 'technology', 'software', 'hardware'],
        'Design': ['design', 'logo', 'branding'],
        'Controversy': ['controversy', 'debate', 'issue']
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

def generate_social_trend(text):
    words = text.split()[:2]  # Use first two words of the story
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#CreativeBloq"

# No Flask app or route decorators in this file