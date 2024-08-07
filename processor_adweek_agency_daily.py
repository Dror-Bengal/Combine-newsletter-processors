import re
import json
import random
import requests
from flask import jsonify
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG)

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        metadata = {
            "date": data['metadata'].get('date'),
            "sender": data['metadata'].get('sender'),
            "subject": data['metadata'].get('subject'),
            "Sender name": data['metadata'].get('Sender name')
        }
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = extract_content_blocks(soup)
        
        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }
        
        return jsonify(output_json), 200

    except Exception as e:
        logging.error(f"Error in process_email: {str(e)}")
        return jsonify({"error": str(e)}), 500

def extract_content_blocks(soup):
    content_blocks = []
    score = 1
    seen_content = set()

    # Find all potential content blocks
    blocks = soup.find_all(['table', 'div'], class_=['em_wrapper'])

    for block in blocks:
        # Extract title
        title_elem = block.find(['span', 'td'], class_='em_font_18')
        if title_elem and title_elem.a:
            title = title_elem.a.text.strip()
            link = title_elem.a.get('href', '')
        else:
            continue  # Skip blocks without a title

        # Check for duplicates
        if title in seen_content:
            continue
        seen_content.add(title)

        # Extract image
        img_elem = block.find('img', class_='em_full_img')
        image = img_elem['src'] if img_elem else ''

        # Extract description
        desc_elem = block.find(['span', 'td'], class_='em_font_15')
        description = desc_elem.text.strip() if desc_elem else ''

        # Create content block
        content_block = {
            "text": title,
            "link": link,
            "image": image,
            "description": description,
            "enrichment_text": generate_enrichment_text(link),
            "main_category": "Newsletter",
            "sub_category": determine_sub_category(title),
            "social_trend": generate_social_trend(title),
            "scoring": score
        }

        content_blocks.append(content_block)
        score += 1

    return content_blocks

def generate_enrichment_text(link):
    text = get_adweek_article(link)
    if text.startswith("Error") or text == "Article content not available.":
        return f"Unable to fetch article content. {text}"
    return text[:500] + "..."  # Trim to first 500 characters

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
    words = text.split()[:2]  # Use first two words of the title
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#AdweekTrend"

def get_adweek_article(url):
    """Fetches an AdWeek article and parses it for the article body and all included links."""
    logging.info(f"Attempting to fetch article from: {url}")
    
    try:
        # Random user agents for each request
        _useragent_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.62',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0'
        ]

        # Get article with requests
        response = requests.get(
            url=url,
            headers={
                "User-Agent": random.choice(_useragent_list)
            },
            timeout=10  # Add a timeout to prevent hanging
        )
        response.raise_for_status()  # Raise an exception for bad status codes

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        doc_object = soup.find('script', type='application/ld+json')

        if doc_object:
            json_ld_content: dict = json.loads(doc_object.string)

            # HTML type string containing the full article content
            if json_ld_content.get('sharedContent'):
                article_body = json_ld_content['sharedContent'].get('articleBody', '')
            else:
                article_body = json_ld_content.get('articleBody', '')
            
            if not article_body:
                logging.warning(f"No article body found for URL: {url}")
                return "Article content not available."
            
            return article_body
        else:
            logging.warning(f"No ld+json script found for URL: {url}")
            return "Article content not available."

    except requests.RequestException as e:
        logging.error(f"Error fetching article from {url}: {str(e)}")
        return f"Error fetching article: {str(e)}"
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON from {url}: {str(e)}")
        return "Error parsing article content."
    except Exception as e:
        logging.error(f"Unexpected error processing article from {url}: {str(e)}")
        return "Unexpected error processing article."

# Flask route and app.run() should be in the main app.py file, not here