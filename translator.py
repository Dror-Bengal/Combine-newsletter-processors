import os
import json
from google.oauth2 import service_account
from google.cloud import translate_v2 as translate
from cachetools import TTLCache
import logging

logging.basicConfig(level=logging.DEBUG)

# Initialize the Google Translate client
credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '/etc/secrets/birzia-translation-abd35ea601c2.json')
try:
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    translate_client = translate.Client(credentials=credentials)
    logging.debug("Translate client initialized successfully with service account file")
except Exception as e:
    logging.error(f"Error initializing translate client: {str(e)}")
    raise

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