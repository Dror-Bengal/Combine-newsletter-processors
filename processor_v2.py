import logging
import re
import urllib.parse
from flask import jsonify
from bs4 import BeautifulSoup
import requests
import spacy
import os
from requests.exceptions import RequestException, Timeout, TooManyRedirects
from urllib3.exceptions import MaxRetryError
import time
from functools import wraps
from time import time as current_time
from tenacity import retry, stop_after_attempt, wait_exponential
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.DEBUG)

# Check if the model is installed, if not, download it
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logging.info("Downloading spaCy model...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class CircuitBreaker:
    def __init__(self, max_failures=3, reset_time=300):
        self.max_failures = max_failures
        self.reset_time = reset_time
        self.failures = {}

    def __call__(self, func):
        @wraps(func)
        def wrapper(url, *args, **kwargs):
            if url in self.failures:
                if self.failures[url]['count'] >= self.max_failures and time.time() - self.failures[url]['time'] < self.reset_time:
                    logging.warning(f"Circuit breaker open for {url}")
                    return {"error": "Circuit breaker open"}
                elif time.time() - self.failures[url]['time'] >= self.reset_time:
                    self.failures[url] = {'count': 0, 'time': time.time()}
            
            try:
                result = func(url, *args, **kwargs)
                self.failures[url] = {'count': 0, 'time': time.time()}
                return result
            except Exception as e:
                if url not in self.failures:
                    self.failures[url] = {'count': 1, 'time': time.time()}
                else:
                    self.failures[url]['count'] += 1
                    self.failures[url]['time'] = time.time()
                raise
        return wrapper

circuit_breaker = CircuitBreaker(max_failures=3, reset_time=300)

def process_email(data):
    logging.debug(f"Received data in process_email: {data}")
    try:
        if not data or 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            logging.error(f"Invalid JSON structure: {data}")
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        logging.debug(f"Content HTML (first 500 chars): {content_html[:500]}")
        logging.debug(f"Metadata: {metadata}")
        
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = []
        score = 1

        for block in soup.find_all(['div', 'table'], class_=lambda x: x and ('content-block' in x or 'hse-column' in x)):
            block_data = process_block(block, score)
            if block_data:
                if 'link' in block_data:
                    enriched_data = scrape_and_process(block_data['link'])
                    if 'error' in enriched_data:
                        logging.warning(f"Error enriching block: {enriched_data['error']}")
                    else:
                        block_data.update(enriched_data)
                
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
        "image": "",  # Initialize with empty string
        "link": "",   # Initialize with empty string
        "text": ""    # Initialize with empty string
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

@circuit_breaker(max_failures=3, reset_time=300)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
@circuit_breaker
def scrape_and_process(url, max_redirects=5):
    try:
        logging.info(f"Attempting to scrape content from {url}")
        time.sleep(2)  # 2-second delay to respect rate limits
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        for _ in range(max_redirects + 1):
            try:
                response = session.get(url, headers=headers, timeout=60, allow_redirects=False)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed for {url}: {str(e)}")
                raise
            
            if response.is_redirect:
                if 'Location' in response.headers:
                    url = response.headers['Location']
                    logging.info(f"Following redirect to: {url}")
                else:
                    logging.error("Redirect without Location header")
                    return {"error": "Redirect without Location header"}
            else:
                break
        else:
            logging.error(f"Too many redirects when scraping content from {url}")
            return {"error": f"Too many redirects when fetching content from {url}"}
        
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Response URL: {response.url}")
        
        if "You're being redirected" in response.text:
            logging.info("Detected redirect page, attempting to find the actual content URL")
            soup = BeautifulSoup(response.text, 'html.parser')
            redirect_link = soup.find('a', href=True)
            if redirect_link:
                actual_url = redirect_link['href']
                logging.info(f"Found actual content URL: {actual_url}")
                return scrape_and_process(actual_url, max_redirects - 1)
            else:
                logging.error("Could not find redirect link")
                return {"error": "Redirect link not found"}
        
        logging.info("Successfully retrieved content, parsing with BeautifulSoup")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract full article text
        article_text = soup.get_text(strip=True)
        logging.debug(f"Extracted text (first 100 chars): {article_text[:100]}...")
        
        # Extract YouTube or Vimeo links
        video_links = extract_video_links(soup)
        logging.debug(f"Found {len(video_links)} video links")
        
        # Process text with spaCy
        doc = nlp(article_text)
        
        logging.info("Generating summary and extracting information")
        summary = generate_summary(doc)
        must_know_points = generate_must_know_points(doc)
        customers = extract_customers(doc)
        tags = generate_tags(doc)
        relevancy = calculate_relevancy(doc)
        
        logging.info("Scraping and processing completed successfully")
        return {
            "enrichment_text": article_text[:1000],  # Limit to first 1000 characters
            "short_summary": summary,
            "must_know_points": must_know_points,
            "customers": customers,
            "tags": tags,
            "video_links": video_links,
            "relevancy": relevancy,
        }
    except Exception as e:
        logging.error(f"Unexpected error scraping content from {url}: {str(e)}")
        raise

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
    score += len(block_data.get('enrichment_text', '')) / 1000  # 1 point per 1000 characters
    score += len(block_data.get('video_links', [])) * 2  # 2 points per video link
    score += len(block_data.get('relevancy', []))  # 1 point per relevant customer
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