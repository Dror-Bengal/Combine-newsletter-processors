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
    logger.error("GOOGLE_TRANSLATE_API_KEY environment variable is not set")
    raise EnvironmentError("GOOGLE_TRANSLATE_API_KEY environment variable is not set")

logger.debug("API key retrieved successfully")

# Initialize a cache with a time-to-live of 1 day and max size of 1000 items
cache = TTLCache(maxsize=1000, ttl=86400)

def translate_text(text, target_language='he', chunk_size=5000):
    """
    Translate text to the target language using Google Translate API.
    Uses caching to avoid unnecessary API calls and chunks long texts.
    """
    if not text:  # Handle empty strings
        return text

    cache_key = f"{text[:100]}:{target_language}"  # Use first 100 chars for cache key
    if cache_key in cache:
        return cache[cache_key]
    
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    translated_chunks = []

    for chunk in chunks:
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                'q': chunk,
                'target': target_language,
                'key': api_key
            }
            response = requests.post(url, params=params)
            response.raise_for_status()
            result = response.json()
            translated_chunks.append(result['data']['translations'][0]['translatedText'])
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            translated_chunks.append(chunk)  # Use original text if translation fails

    translated_text = ' '.join(translated_chunks)
    cache[cache_key] = translated_text
    return translated_text

def translate_long_text(text, target_language='he', max_length=5000):
    """
    Translate long text by splitting it into chunks.
    """
    return translate_text(text, target_language, max_length)

def translate_content_block(block, target_language='he'):
    """
    Translate the 'text', 'description', and 'enrichment_text' fields of a content block.
    """
    for field in ['text', 'description', 'enrichment_text']:
        if field in block and block[field]:
            logger.info(f"Translating {field} (length: {len(block[field])})")
            block[f'translated_{field}'] = translate_text(block[field], target_language)
    return block

@shared_task
def translate_content_block_async(block, target_language='he'):
    return translate_content_block(block, target_language)

logger.debug("translator.py loaded successfully")