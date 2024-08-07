from flask import jsonify
from bs4 import BeautifulSoup
import logging
from translator import translate_text  # Import the translation function

logging.basicConfig(level=logging.DEBUG)

def process_email(data):
    logging.debug(f"Received request data: {data}")
    try:
        if 'metadata' not in data or 'content' not in data['metadata']:
            raise KeyError("Missing 'content' key in the 'metadata' section of the JSON payload")

        content = data['metadata']['content']['html']
        metadata = data['metadata']
        
        logging.debug(f"Content: {content}")
        logging.debug(f"Metadata: {metadata}")

        # Extract stories from the HTML content
        content_blocks = extract_stories(content)
        
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
    content_blocks = soup.find_all(['table', 'div'], class_=['table-mobile', 'newsletter-advertisement'])
    
    score = 1  # Initialize score to 1
    
    for block in content_blocks:
        # Check if it's an ad
        if 'newsletter-advertisement' in block.get('class', []):
            continue  # Skip ads, but don't increment score
        
        story = {'scoring': score}  # Add the score to the story dict
        score += 1  # Increment score for next item
        
        # Extract text
        text_element = block.find(['h2', 'h3', 'p'])
        if text_element:
            story['text'] = text_element.text.strip()
            story['translated_text'] = translate_text(story['text'])
        
        # Extract link
        link_element = block.find('a')
        if link_element:
            story['link'] = link_element.get('href', '')
        
        # Extract image
        img_element = block.find('img', class_='responsiveimage')
        if img_element:
            story['image'] = img_element.get('src', '')
        
        # Add other required fields
        story['enrichment_text'] = generate_enrichment_text(story.get('text', ''))
        story['main_category'] = "Newsletter"
        story['sub_category'] = determine_sub_category(story.get('text', ''))
        story['social_trend'] = generate_social_trend(story.get('text', ''))
        
        # Add translated description if there's a description
        if 'description' in story:
            story['translated_description'] = translate_text(story['description'])
        else:
            story['translated_description'] = ""
        
        stories.append(story)
    
    return stories
    
def generate_enrichment_text(text):
    # This is a placeholder. In a real scenario, you might use NLP or AI to generate this.
    return f"Enriched version of: {text[:50]}..."

def determine_sub_category(text):
    # This is a simple example. You might use more sophisticated categorization in reality.
    categories = {
        'OpenAI': ['AI', 'machine learning', 'GPT'],
        'Marketing': ['ad', 'campaign', 'brand'],
        'Technology': ['tech', 'software', 'hardware'],
        'Sports': ['Olympics', 'athlete', 'game']
    }
    
    for category, keywords in categories.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return category
    return "General"

def generate_social_trend(text):
    # This is a simple example. You might use actual trending topics or AI-generated trends.
    words = text.split()[:2]  # Use first two words of the story
    return f"#{words[0]}{words[1]}" if len(words) > 1 else "#Trending"

# Remove the Flask route and app.run() call from this file