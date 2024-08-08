import logging
import random  # Add this line to import the random module
from bs4 import BeautifulSoup
from flask import jsonify
from translator import translate_text, translate_content_block_async
import requests
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return {"error": "Invalid JSON structure"}, 400

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
        
        return output_json, 200

    except Exception as e:
        logger.error(f"Error in process_email: {str(e)}")
        return {"error": str(e)}, 500

def extract_content_blocks(soup):
    content_blocks = []
    
    # Extract main story
    main_story = extract_main_story(soup)
    if main_story:
        content_blocks.append(main_story)
    
    # Extract Today's Top Stories
    top_stories = extract_top_stories(soup)
    content_blocks.extend(top_stories)
    
    # Extract More News & Highlights
    more_news = extract_more_news(soup)
    content_blocks.extend(more_news)
    
    # Extract One More Thing
    one_more_thing = extract_one_more_thing(soup)
    if one_more_thing:
        content_blocks.append(one_more_thing)
    
    return content_blocks

def extract_main_story(soup):
    # Implementation for extracting the main story
    pass

def extract_top_stories(soup):
    # Implementation for extracting Today's Top Stories
    pass

def extract_more_news(soup):
    # Implementation for extracting More News & Highlights
    pass

def extract_one_more_thing(soup):
    # Implementation for extracting One More Thing
    pass

def generate_enrichment_text(link):
    # Implementation for generating enrichment text from the link
    pass

def determine_sub_category(text):
    # Implementation for determining the sub-category
    pass

def generate_social_trend(text):
    # Implementation for generating social trend
    pass
def extract_main_story(soup):
    main_story = soup.find('div', class_='content-block')
    if main_story:
        headline = main_story.find('h2').text.strip() if main_story.find('h2') else ''
        link = main_story.find('a')['href'] if main_story.find('a') else ''
        image = main_story.find('img')['src'] if main_story.find('img') else ''
        text = main_story.find('p').text.strip() if main_story.find('p') else ''
        
        return {
            'text': headline,
            'link': link,
            'image': image,
            'description': text,
            'scoring': 1,
            'enrichment_text': generate_enrichment_text(link),
            'main_category': "Newsletter",
            'sub_category': determine_sub_category(headline),
            'social_trend': generate_social_trend(headline)
        }
    return None

def extract_top_stories(soup):
    top_stories = []
    stories_section = soup.find('div', text="Today's Top Stories").find_next('table') if soup.find('div', text="Today's Top Stories") else None
    if stories_section:
        for idx, story in enumerate(stories_section.find_all('tr'), start=2):
            headline = story.find('h3').text.strip() if story.find('h3') else ''
            link = story.find('a')['href'] if story.find('a') else ''
            image = story.find('img')['src'] if story.find('img') else ''
            
            top_stories.append({
                'text': headline,
                'link': link,
                'image': image,
                'description': '',
                'scoring': idx,
                'enrichment_text': generate_enrichment_text(link),
                'main_category': "Newsletter",
                'sub_category': determine_sub_category(headline),
                'social_trend': generate_social_trend(headline)
            })
    return top_stories

def extract_more_news(soup):
    more_news = []
    news_section = soup.find('div', text="More News & Highlights")
    if news_section:
        for idx, item in enumerate(news_section.find_next('table').find_all('tr'), start=6):
            text = item.text.strip()
            link = item.find('a')['href'] if item.find('a') else ''
            
            more_news.append({
                'text': text,
                'link': link,
                'image': '',
                'description': '',
                'scoring': idx,
                'enrichment_text': generate_enrichment_text(link),
                'main_category': "Newsletter",
                'sub_category': determine_sub_category(text),
                'social_trend': generate_social_trend(text)
            })
    return more_news

def extract_one_more_thing(soup):
    one_more = soup.find('div', text="One More Thing")
    if one_more:
        text = one_more.find_next('p').text.strip() if one_more.find_next('p') else ''
        image = one_more.find_next('img')['src'] if one_more.find_next('img') else ''
        link = one_more.find_next('a')['href'] if one_more.find_next('a') else ''
        
        return {
            'text': "One More Thing: " + text,
            'link': link,
            'image': image,
            'description': '',
            'scoring': len(extract_more_news(soup)) + 6,
            'enrichment_text': generate_enrichment_text(link),
            'main_category': "Newsletter",
            'sub_category': "One More Thing",
            'social_trend': generate_social_trend(text)
        }
    return None

def generate_enrichment_text(link):
    try:
        article_body = get_adweek_article(link)
        if article_body != "Article content not available.":
            return article_body[:500]  # Limit to 500 characters
    except Exception as e:
        logger.error(f"Error generating enrichment text: {str(e)}")
    return ""

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

def determine_sub_category(text):
    categories = {
        'Advertising': ['ad', 'campaign', 'creative'],
        'Digital': ['digital', 'online', 'social media'],
        'TV': ['TV', 'television', 'streaming'],
        'Marketing': ['marketing', 'brand', 'strategy'],
        'Technology': ['tech', 'AI', 'platform'],
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

def generate_social_trend(text):
    words = text.split()[:2]
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#AdweekTrend"