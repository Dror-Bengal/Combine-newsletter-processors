import os
import json
from google.oauth2 import service_account
from google.cloud import translate_v2 as translate
from cachetools import TTLCache
import logging

logging.basicConfig(level=logging.DEBUG)

# Initialize the Google Translate client
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    logging.debug("GOOGLE_APPLICATION_CREDENTIALS environment variable found")
    if os.environ['GOOGLE_APPLICATION_CREDENTIALS'].startswith('{'):
        logging.debug("Credentials appear to be a JSON string")
        credentials_info = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        translate_client = translate.Client(credentials=credentials)
    else:
        logging.debug("Using default file-based credentials")
        translate_client = translate.Client()
else:
    logging.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")

logging.debug("Translate client initialized successfully")

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