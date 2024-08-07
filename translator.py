import os
from google.cloud import translate_v2 as translate
from cachetools import TTLCache
import logging

logging.basicConfig(level=logging.DEBUG)

# Initialize the Google Translate client with API key
api_key = os.environ.get('GOOGLE_TRANSLATE_API_KEY')
if not api_key:
    logging.error("GOOGLE_TRANSLATE_API_KEY environment variable is not set")
    raise EnvironmentError("GOOGLE_TRANSLATE_API_KEY environment variable is not set")

translate_client = translate.Client.from_api_key(api_key)
logging.debug("Translate client initialized successfully with API key")

# Initialize a cache with a time-to-live of 1 day and max size of 1000 items
cache = TTLCache(maxsize=1000, ttl=86400)

def translate_text(text, target_language='es'):
    """
    Translate text to the target language.
    Uses caching to avoid unnecessary API calls.
    """
    if not text:  # Added to handle empty strings
        return text

    cache_key = f"{text}:{target_language}"
    if cache_key in cache:
        return cache[cache_key]
    
    try:
        result = translate_client.translate(text, target_language=target_language)
        translated_text = result['translatedText']
        cache[cache_key] = translated_text
        return translated_text
    except Exception as e:
        logging.error(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails

def translate_content_block(block, target_language='es'):
    """
    Translate the 'text' and 'description' fields of a content block.
    """
    if 'text' in block:
        block['translated_text'] = translate_text(block['text'], target_language)
    if 'description' in block:
        block['translated_description'] = translate_text(block['description'], target_language)
    return block

# Add this function for asynchronous translation
from celery import shared_task

@shared_task
def translate_content_block_async(block, target_language='es'):
    return translate_content_block(block, target_language)