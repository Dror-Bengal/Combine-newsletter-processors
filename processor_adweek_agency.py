import re
import json
import random
import requests
from bs4 import BeautifulSoup
import logging
from translator import translate_text, translate_long_text
from celery import shared_task
import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata):
    return {
        "metadata": {
            "source_name": "Adweek Advertising & Agency Daily",
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

@shared_task
def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return {"error": "Invalid JSON structure"}, 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        output_json = create_base_output_structure(metadata)
        
        # Convert HTML to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False
        output_json['content']['main_content_text'] = h.handle(content_html)
        output_json['content']['translated_main_content_text'] = translate_long_text(output_json['content']['main_content_text'])
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        output_json['content']['content_blocks'] = content_blocks
        
        return output_json, 200

    except Exception as e:
        logger.error(f"Error in process_email: {str(e)}")
        return {"error": str(e)}, 500

def extract_content_blocks(soup):
    content_blocks = []
    score = 1
    seen_content = set()

    blocks = soup.find_all(['table', 'div'], class_=['em_wrapper'])

    for block in blocks:
        title_elem = block.find(['span', 'td'], class_='em_font_18')
        if title_elem and title_elem.a:
            title = title_elem.a.text.strip()
            link = title_elem.a.get('href', '')
        else:
            continue

        if title in seen_content:
            continue
        seen_content.add(title)

        img_elem = block.find('img', class_='em_full_img')
        image = img_elem['src'] if img_elem else ''

        desc_elem = block.find(['span', 'td'], class_='em_font_15')
        description = desc_elem.text.strip() if desc_elem else ''

        enrichment_text = generate_enrichment_text(link)

        content_block = {
            "block_type": "article",
            "title": title,
            "translated_title": translate_text(title),
            "description": description,
            "translated_description": translate_text(description),
            "body_text": enrichment_text,
            "translated_body_text": translate_long_text(enrichment_text),
            "image_url": image,
            "link_url": link,
            "category": "Newsletter",
            "subcategory": determine_sub_category(title),
            "social_trend": generate_social_trend(title),
            "translated_social_trend": translate_text(generate_social_trend(title)),
            "scoring": score,
        }

        content_blocks.append(content_block)
        score += 1

    return content_blocks

def generate_enrichment_text(link):
    text = get_adweek_article(link)
    if text.startswith("Error") or text == "Article content not available.":
        return f"Unable to fetch article content. {text}"
    return text

def determine_sub_category(text):
    categories = {
        'Agency': ['agency', 'firm', 'company'],
        'Campaign': ['campaign', 'ad', 'commercial'],
        'Brand': ['brand', 'product', 'company'],
        'Digital': ['digital', 'online', 'social media'],
        'Creative': ['creative', 'design', 'art'],
        'Media': ['media', 'publisher', 'platform'],
        'Marketing': ['marketing', 'strategy', 'promotion']
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

def generate_social_trend(text):
    words = text.split()[:2]
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#AdweekTrend"

def get_adweek_article(url):
    logger.info(f"Attempting to fetch article from: {url}")
    
    try:
        _useragent_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.62',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0'
        ]

        response = requests.get(
            url=url,
            headers={
                "User-Agent": random.choice(_useragent_list)
            },
            timeout=10
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        doc_object = soup.find('script', type='application/ld+json')

        if doc_object:
            json_ld_content: dict = json.loads(doc_object.string)

            if json_ld_content.get('sharedContent'):
                article_body = json_ld_content['sharedContent'].get('articleBody', '')
            else:
                article_body = json_ld_content.get('articleBody', '')
            
            if not article_body:
                logger.warning(f"No article body found for URL: {url}")
                return "Article content not available."
            
            return article_body
        else:
            logger.warning(f"No ld+json script found for URL: {url}")
            return "Article content not available."

    except requests.RequestException as e:
        logger.error(f"Error fetching article from {url}: {str(e)}")
        return f"Error fetching article: {str(e)}"
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from {url}: {str(e)}")
        return "Error parsing article content."
    except Exception as e:
        logger.error(f"Unexpected error processing article from {url}: {str(e)}")
        return "Unexpected error processing article."

# End of processor_adweek_agency_daily.py