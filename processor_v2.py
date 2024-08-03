from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import logging
import re
import urllib.parse

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

@app.route('/process_newsletter', methods=['POST'])
def process_newsletter():
    try:
        data = request.get_json()
        logging.debug(f"Parsed JSON: {data}")
        
        if not data or 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return jsonify({"error": "Invalid JSON structure"}), 400

        content_html = data['metadata']['content']['html']
        soup = BeautifulSoup(content_html, 'html.parser')

        content_blocks = []
        score = 1

        # Find all potential content blocks
        for block in soup.find_all(['div', 'table'], class_=lambda x: x and ('content-block' in x or 'hse-column' in x)):
            block_data = {
                "enrichment_text": "The quick brown fox jumps over the lazy dog near the quiet riverbank...",
                "image": "",
                "link": "",
                "main_category": "Newsletter",
                "scoring": score,
                "social_trend": "",
                "sub_category": "OpenAI",
                "text": ""
            }

            # Extract images
            img_tag = block.find('img')
            if img_tag:
                if 'src' in img_tag.attrs:
                    # Extract the full image URL
                    img_url = img_tag['src']
                    if img_url.startswith('https://ci3.googleusercontent.com'):
                        # Extract the original URL from the Google proxy
                        parsed_url = urllib.parse.urlparse(img_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        if 'url' in query_params:
                            img_url = query_params['url'][0]
                    block_data['image'] = img_url

            # Extract links
            link_tag = block.find('a')
            if link_tag and 'href' in link_tag.attrs:
                block_data['link'] = link_tag['href']

            # Extract text
            text = block.get_text(strip=True)
            # Remove any text that's too long (likely aggregated from multiple blocks)
            if len(text) > 500:
                text = text[:500] + "..."
            
            # Remove specific phrases
            text = re.sub(r'(See Feature|See Full Series|ADVERTISING|See Campaign)', '', text, flags=re.IGNORECASE)
            
            # Remove any trailing whitespace or punctuation
            text = re.sub(r'[^\w]+$', '', text.strip())
            
            block_data['text'] = text

            # Only add block if it has meaningful content
            if block_data['text'] and (block_data['image'] or block_data['link']):
                # Exclude blocks that only contain "ADVERTISING"
                if block_data['text'].lower() != "advertising":
                    content_blocks.append(block_data)
                    score += 1

        # Remove duplicate blocks
        unique_blocks = []
        seen = set()
        for block in content_blocks:
            block_key = (block['image'], block['link'], block['text'][:100])  # Use first 100 chars of text for comparison
            if block_key not in seen:
                seen.add(block_key)
                unique_blocks.append(block)

        # Exclude social and address blocks
        final_blocks = [block for block in unique_blocks if not (
            "Follow Us" in block['text'] or 
            "The Clios, 104 West 27th Street" in block['text']
        )]

        # Reassign scoring to be consecutive
        for i, block in enumerate(final_blocks, start=1):
            block['scoring'] = i

        return jsonify(final_blocks), 200

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process_email', methods=['POST'])
def process_email():
    logging.debug(f"Received request data: {request.data}")
    try:
        data = request.json
        logging.debug(f"Parsed JSON data: {data}")

        if 'metadata' not in data or 'content' not in data['metadata']:
            raise KeyError("Missing 'content' key in the 'metadata' section of the JSON payload")

        content = data['metadata']['content']['html']
        metadata = data['metadata']
        
        logging.debug(f"Content: {content}")
        logging.debug(f"Metadata: {metadata}")

        # Process the email content here
        # For now, we'll just return the metadata and a placeholder for content_blocks
        output_json = {
            "metadata": metadata,
            "content_blocks": [{"placeholder": "Content processing logic to be implemented"}]
        }
        
        logging.debug(f"Final output JSON: {output_json}")
        
        return jsonify(output_json), 200
    except KeyError as e:
        logging.error(f"KeyError: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error processing email: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)