import logging
import re
import urllib.parse
from flask import jsonify
from bs4 import BeautifulSoup
import requests
import spacy

logging.basicConfig(level=logging.DEBUG)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def process_email(data):
    logging.debug(f"Received data in process_email: {data}")
    try:
        if not data or 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = []
        score = 1

        for block in soup.find_all(['div', 'table'], class_=lambda x: x and ('content-block' in x or 'hse-column' in x)):
            block_data = process_block(block, score)
            if block_data:
                content_blocks.append(block_data)
                score += 1

        # Remove duplicate blocks
        unique_blocks = remove_duplicates(content_blocks)

        # Exclude social and address blocks
        final_blocks = [block for block in unique_blocks if not (
            "Follow Us" in block['text'] or 
            "The Clios, 104 West 27th Street" in block['text']
        )]

        # Reassign scoring to be consecutive
        for i, block in enumerate(final_blocks, start=1):
            block['scoring'] = i

        output_json = {
            "metadata": metadata,
            "content_blocks": final_blocks
        }

        logging.debug(f"Processed output: {output_json}")
        return jsonify(output_json), 200

    except Exception as e:
        logging.error(f"Error processing email: {str(e)}")
        return jsonify({"error": str(e)}), 500

def process_block(block, score):
    block_data = {
        "scoring": score,
        "main_category": "Newsletter",
        "sub_category": "Advertising",
        "social_trend": "",
    }

    # Extract image
    img_tag = block.find('img')
    if img_tag and 'src' in img_tag.attrs:
        block_data['image'] = clean_image_url(img_tag['src'])

    # Extract link
    link_tag = block.find('a')
    if link_tag and 'href' in link_tag.attrs:
        block_data['link'] = link_tag['href']

    # Extract text
    text = block.get_text(strip=True)
    block_data['text'] = clean_text(text)

    # Only process block if it has meaningful content
    if block_data['text'] and (block_data['image'] or block_data['link']):
        if block_data['text'].lower() != "advertising":
            # Scrape and process additional content
            enriched_data = scrape_and_process(block_data['link'])
            block_data.update(enriched_data)
            
            # Calculate total score
            block_data['total_score'] = calculate_total_score(block_data)

            return block_data
    
    return None

def clean_image_url(url):
    if url.startswith('https://ci3.googleusercontent.com'):
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'url' in query_params:
            return query_params['url'][0]
    return url

def clean_text(text):
    text = re.sub(r'(See Feature|See Full Series|ADVERTISING|See Campaign)', '', text, flags=re.IGNORECASE)
    return re.sub(r'[^\w]+$', '', text.strip())

def scrape_and_process(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        article_soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract full article text
        article_text = article_soup.get_text(strip=True)
        
        # Extract YouTube or Vimeo links
        video_links = extract_video_links(article_soup)
        
        # Process text with spaCy
        doc = nlp(article_text)
        
        return {
            "enrichment_text": article_text,
            "short_summary": generate_summary(doc),
            "must_know_points": generate_must_know_points(doc),
            "customers": extract_customers(doc),
            "tags": generate_tags(doc),
            "video_links": video_links,
            "relevancy": calculate_relevancy(doc),
        }
    except Exception as e:
        logging.error(f"Error scraping content: {str(e)}")
        return {
            "enrichment_text": "Error fetching additional content",
            "short_summary": "",
            "must_know_points": [],
            "customers": [],
            "tags": [],
            "video_links": [],
            "relevancy": [],
        }

def extract_video_links(soup):
    video_links = []
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if 'youtube.com' in src or 'vimeo.com' in src:
            video_links.append(src)
    return video_links

def generate_summary(doc):
    return ' '.join([sent.text for sent in doc.sents][:3])

def generate_must_know_points(doc):
    return [sent.text for sent in doc.sents if any(token.pos_ == 'VERB' for token in sent)][:5]

def extract_customers(doc):
    return list(set([ent.text for ent in doc.ents if ent.label_ == 'ORG']))

def generate_tags(doc):
    return list(set([token.lemma_ for token in doc if token.pos_ in ['NOUN', 'PROPN'] and len(token.text) > 2]))[:10]

def calculate_relevancy(doc):
    # This is a placeholder. In a real scenario, you'd have a list of customers and their industries.
    customers = {
        "TechCorp": "Technology",
        "FashionBrand": "Fashion",
        "FoodChain": "Food",
    }
    
    relevancy = []
    doc_text = doc.text.lower()
    
    for customer, industry in customers.items():
        if industry.lower() in doc_text or customer.lower() in doc_text:
            relevancy.append(customer)
    
    return relevancy

def calculate_total_score(block_data):
    score = block_data['scoring']
    score += len(block_data['enrichment_text']) / 1000  # 1 point per 1000 characters
    score += len(block_data['video_links']) * 2  # 2 points per video link
    score += len(block_data['relevancy'])  # 1 point per relevant customer
    return int(score)

def remove_duplicates(blocks):
    unique_blocks = []
    seen = set()
    for block in blocks:
        block_key = (block['image'], block['link'], block['text'][:100])
        if block_key not in seen:
            seen.add(block_key)
            unique_blocks.append(block)
    return unique_blocks

# No Flask app or route decorators in this file