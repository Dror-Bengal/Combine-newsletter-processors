from flask import jsonify
from bs4 import BeautifulSoup
import logging
import re

logging.basicConfig(level=logging.DEBUG)

def process_email(data):
    logging.debug(f"Received request data: {data}")
    try:
        if 'metadata' not in data or 'content' not in data['metadata']:
            raise KeyError("Missing 'content' key in the 'metadata' section of the JSON payload")

        content_html = data['metadata']['content']['html']
        metadata = data['metadata']
        
        logging.debug(f"Content: {content_html}")
        logging.debug(f"Metadata: {metadata}")

        # Extract stories from the HTML content
        content_blocks = extract_stories(content_html)
        
        logging.debug(f"Extracted content blocks: {content_blocks}")

        output_json = {
            "metadata": metadata,
            "content_blocks": content_blocks
        }
        
        logging.debug(f"Final output JSON: {output_json}")
        
        return jsonify(output_json), 200
    except KeyError as e:
        logging.error(f"KeyError: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error processing email: {str(e)}")
        return jsonify({"error": str(e)}), 400

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
            story_data = {'scoring': score}
            
            # Extract headline
            headline = story.find('div', attrs={'data-testid': 'copy_headline'})
            if headline:
                story_data['text'] = headline.text.strip()
            
            # Extract link
            link = story.find('a', attrs={'data-testid': 'cta_link'})
            if link:
                story_data['link'] = link['href']
            
            # Extract image
            img = story.find('img', class_='scale_full_width')
            if img:
                story_data['image'] = img['src']
            
            # Add other required fields
            story_data['enrichment_text'] = generate_enrichment_text(story_data.get('text', ''))
            story_data['main_category'] = main_category
            story_data['sub_category'] = determine_sub_category(story_data.get('text', ''))
            story_data['social_trend'] = generate_social_trend(story_data.get('text', ''))
            
            if story_data.get('text') and (story_data.get('image') or story_data.get('link')):
                stories.append(story_data)
                score += 1  # Increment score for next item
    
    return stories

def generate_enrichment_text(text):
    # This is a placeholder. In a real scenario, you might use NLP or AI to generate this.
    return f"Enriched version of: {text[:50]}..."

def determine_sub_category(text):
    # This is a simple example. You might use more sophisticated categorization in reality.
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
    # This is a simple example. You might use actual trending topics or AI-generated trends.
    words = text.split()[:2]  # Use first two words of the story
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#Trending"