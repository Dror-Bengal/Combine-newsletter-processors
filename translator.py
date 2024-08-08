import os
import requests
from cachetools import TTLCache
import logging
from celery import shared_task

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

    cache_key = f"{text[:100]}:{target_language}"  # Use first 100 chars for cache key
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

def translate_long_text(text, target_language='he', max_length=5000):
    """
    Translate long text by splitting it into chunks.
    """
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    translated_chunks = [translate_text(chunk, target_language) for chunk in chunks]
    return ' '.join(translated_chunks)

def translate_content_block(block, target_language='he'):
    """
    Translate the 'text', 'description', and 'enrichment_text' fields of a content block.
    """
    for field in ['text', 'description', 'enrichment_text']:
        if field in block and block[field]:
            logger.info(f"Translating {field} (length: {len(block[field])})")
            if len(block[field]) > 5000:
                block[f'translated_{field}'] = translate_long_text(block[field], target_language)
            else:
                block[f'translated_{field}'] = translate_text(block[field], target_language)
    return block

@shared_task
def translate_content_block_async(block, target_language='he'):
    return translate_content_block(block, target_language)

logger.debug("translator.py loaded successfully")