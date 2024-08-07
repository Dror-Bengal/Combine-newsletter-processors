import os
import requests
from cachetools import TTLCache
import logging
from celery import shared_task

logging.basicConfig(level=logging.DEBUG)

# Get the API key from environment variable
api_key = os.environ.get('GOOGLE_TRANSLATE_API_KEY')
if not api_key:
    logging.error("GOOGLE_TRANSLATE_API_KEY environment variable is not set")
    raise EnvironmentError("GOOGLE_TRANSLATE_API_KEY environment variable is not set")

logging.debug("API key retrieved successfully")

# Initialize a cache with a time-to-live of 1 day and max size of 1000 items
cache = TTLCache(maxsize=1000, ttl=86400)

def translate_text(text, target_language='he'):
    """
    Translate text to the target language using Google Translate API.
    Uses caching to avoid unnecessary API calls.
    """
    if not text:  # Handle empty strings
        return text

    cache_key = f"{text}:{target_language}"
    if cache_key in cache:
        return cache[cache_key]
    
    try:
        url = "https://translation.googleapis.com/language/translate/v2"
        params = {
            'q': text,
            'target': target_language,
            'key': api_key
        }
        response = requests.post(url, params=params)
        response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx
        result = response.json()
        translated_text = result['data']['translations'][0]['translatedText']
        cache[cache_key] = translated_text
        return translated_text
    except Exception as e:
        logging.error(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails

def translate_content_block(block, target_language='he'):
    """
    Translate the 'text' and 'description' fields of a content block.
    """
    if 'text' in block:
        block['translated_text'] = translate_text(block['text'], target_language)
    if 'description' in block:
        block['translated_description'] = translate_text(block['description'], target_language)
    return block

@shared_task
def translate_content_block_async(block, target_language='he'):
    return translate_content_block(block, target_language)

logging.debug("translator.py loaded successfully")