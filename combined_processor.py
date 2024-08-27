import logging
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import html2text
import requests
import random

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_base_output_structure(metadata, source_name):
    return {
        "metadata": {
            "source_name": source_name,
            "sender_email": metadata.get('sender', ''),
            "sender_name": metadata.get('Sender name', ''),
            "date_sent": metadata.get('date', ''),
            "subject": metadata.get('subject', ''),
            "email_id": metadata.get('message-id', '')
        },
        "content": {
            "content_blocks": []
        }
    }

def process_email(data):
    try:
        if 'metadata' not in data or 'content' not in data['metadata'] or 'html' not in data['metadata']['content']:
            return {"error": "Invalid JSON structure"}, 400

        metadata = data['metadata']
        sender_email = metadata.get('sender', '').lower()
        sender_name = metadata.get('Sender name', '').lower()

        # Determine which processor to use based on sender information
        processor_function = determine_processor(sender_email, sender_name)
        result, status_code = processor_function(data)

        if status_code == 200 and 'content' in result and 'content_blocks' in result['content']:
            formatted_blocks = []
            for block in result['content']['content_blocks']:
                formatted_block = {
                    "title": block.get('title', ''),
                    "image_url": block.get('image_url', ''),
                    "body_text": block.get('body_text', ''),
                    "link": block.get('link_url', ''),
                    "credit": determine_credit(sender_name)
                }
                formatted_blocks.append(formatted_block)
            result['content']['content_blocks'] = formatted_blocks

        return result, status_code

    except Exception as e:
        logger.exception("Unexpected error in process_email")
        return {"error": str(e)}, 500

def determine_processor(sender_email, sender_name):
    processors = {
        ('sara@axios.com', 'sara fischer'): process_axios_media_trends,
        ('nomercynomalice@mail.profgalloway.com', 'scott galloway'): process_no_mercy_no_malice,
        ('notify@sethgodin.com', 'seth godin'): process_seth_godin,
        ('inspireme@simonsinek.com', 'simon sinek'): process_simon_sinek,
        ('emailteam@emails.hbr.org', 'harvard business review'): process_hbr_management_tip,
        ('dorie@dorieclark.com', 'dorie clark'): process_dorie_clark,
    }
    
    for (email, name), processor in processors.items():
        if email in sender_email and name in sender_name:
            return processor
    
    if 'adweek' in sender_name:
        return process_adweek
    elif 'campaign brief' in sender_name:
        return process_campaign_brief
    elif 'creative bloq' in sender_name:
        return process_creative_bloq
    else:
        return process_generic

def process_axios_media_trends(data):
    # Add your code here to process Axios Media Trends emails
    pass

def determine_credit(sender_name):
    credits = {
        'sara fischer': 'Axios Media Trends',
        'scott galloway': 'No Mercy No Malice',
        'seth godin': "Seth Godin's Blog",
        'simon sinek': "Simon Sinek's Notes to Inspire",
        'harvard business review': 'Harvard Business Review Management Tip',
        'dorie clark': 'Dorie Clark Newsletter',
        'adweek': 'Adweek',
        'campaign brief': 'Campaign Brief',
        'creative bloq': 'Creative Bloq'
    }
    return credits.get(sender_name.lower(), 'Newsletter')

def extract_content_blocks(soup):
    content_blocks = []
    potential_blocks = soup.find_all(['div', 'table', 'tr', 'td'], class_=lambda x: x and any(keyword in x for keyword in ['content', 'article', 'story', 'post']))
    
    for block in potential_blocks:
        title = block.find(['h1', 'h2', 'h3', 'strong'])
        title_text = title.get_text(strip=True) if title else ""
        
        body = block.find(['p', 'div'], class_=lambda x: x and 'body' in x) or block
        body_text = body.get_text(strip=True)
        
        image = block.find('img')
        image_url = image['src'] if image and 'src' in image.attrs else ""
        
        link = block.find('a', href=True)
        link_url = link['href'] if link else ""
        
        if title_text or body_text:
            content_blocks.append({
                "block_type": "article",
                "title": title_text,
                "body_text": body_text,
                "image_url": image_url,
                "link_url": link_url,
            })
    
    return content_blocks

# Generic processor that can handle unknown newsletter formats
def process_generic(data):
    logger.debug("Processing generic email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Generic Newsletter")

    soup = BeautifulSoup(content_html, 'html.parser')
    content_blocks = extract_content_blocks(soup)
    output_json['content']['content_blocks'] = content_blocks

    return output_json, 200

def extract_axios_content_blocks(soup):
    content_blocks = []
    story_sections = soup.find_all('td', class_='post-text')

    for section in story_sections:
        headline = section.find_previous('span', class_='bodytext hed')
        headline_text = headline.text.strip() if headline else ""

        if "Axios Pro Reports" in headline_text or "Today's Media Trends" in headline_text:
            continue

        paragraphs = section.find_all('p')
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])

        if not content.strip() and not headline_text.strip():
            continue

        links = section.find_all('a', href=True)
        link = links[0]['href'] if links else ""

        img = section.find('img')
        image_url = img['src'] if img else ""

        block = {
            "block_type": "article",
            "title": headline_text or "Untitled",
            "body_text": content,
            "image_url": image_url,
            "link_url": link,
        }

        content_blocks.append(block)

    return content_blocks

# No Mercy No Malice Processor
def process_no_mercy_no_malice(data):
    logger.debug("Processing No Mercy No Malice email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "No Mercy No Malice")

    soup = BeautifulSoup(content_html, 'html.parser')
    content_blocks = extract_content_blocks(soup)
    
    if not content_blocks:
        # Fallback to the original extraction method if no blocks were found
        content_blocks = extract_no_mercy_no_malice_content(soup)
    
    output_json['content']['content_blocks'] = content_blocks

    return output_json, 200

def extract_no_mercy_no_malice_content(soup):
    content_blocks = []
    main_content = soup.find('tr', id='content-blocks')

    if main_content:
        content_sections = main_content.find_all('td', class_='dd')
        full_content = "\n\n".join([section.get_text(strip=True) for section in content_sections])

        # Remove footer content
        full_content = re.sub(r'\nP\.S\..+', '', full_content, flags=re.DOTALL)
        full_content = re.sub(r'\nP\.P\.S\..+', '', full_content, flags=re.DOTALL)

        # Extract title
        title_match = re.search(r'^(.+)$', full_content, re.MULTILINE)
        title = title_match.group(1) if title_match else "No Mercy No Malice Insights"

        # Extract image URL
        image = main_content.find('img')
        image_url = image['src'] if image else ""

        # Extract link URL
        link = main_content.find('a', href=True)
        link_url = link['href'] if link else ""

        block = {
            "block_type": "article",
            "title": title[:100],
            "body_text": full_content.strip(),
            "image_url": image_url,
            "link_url": link_url,
        }
        content_blocks.append(block)

    return content_blocks

# Seth Godin Processor
def process_seth_godin(data):
    logger.debug("Processing Seth Godin's email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Seth Godin's Blog")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_block = extract_seth_godin_content(soup)
    if content_block:
        output_json['content']['content_blocks'] = [content_block]
    
    return output_json, 200

def extract_seth_godin_content(soup):
    main_image = soup.find('img', class_='c24')
    image_url = main_image['src'] if main_image else ""

    content_container = soup.find('div', class_='rssDesc')
    if content_container:
        headline = content_container.find('h2')
        headline_text = headline.get_text(strip=True) if headline else ""

        paragraphs = content_container.find_all('p')
        content_text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        return {
            "block_type": "article",
            "title": headline_text,
            "body_text": content_text,
            "image_url": image_url,
            "link_url": "",
        }
    return None

# Simon Sinek Processor
def process_simon_sinek(data):
    logger.debug("Processing Simon Sinek's email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Simon Sinek's Notes to Inspire")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_block = extract_simon_sinek_content(soup)
    if content_block:
        output_json['content']['content_blocks'] = [content_block]
    
    return output_json, 200

def extract_simon_sinek_content(soup):
    main_image = soup.find('img', class_='stretch-on-mobile')
    image_url = main_image['src'] if main_image else ""

    content_container = soup.find('div', id=lambda x: x and x.startswith('hs_cos_wrapper_module-0-0-1_'))
    if content_container:
        main_content = content_container.get_text(strip=True)
        return {
            "block_type": "article",
            "title": "Simon Sinek's Note to Inspire",
            "body_text": main_content,
            "image_url": image_url,
            "link_url": "",
        }
    return None

# HBR Management Tip Processor
def process_hbr_management_tip(data):
    logger.debug("Processing HBR Management Tip email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Harvard Business Review Management Tip of the Day")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_block = extract_hbr_management_tip_content(soup)
    if content_block:
        output_json['content']['content_blocks'] = [content_block]
    
    return output_json, 200

def extract_hbr_management_tip_content(soup):
    main_content = soup.find('table', class_='row-content stack')
    if main_content:
        title = main_content.find('h1')
        title_text = title.get_text(strip=True) if title else ""

        content_div = main_content.find('div', style=lambda s: s and 'font-family:Georgia,Times,\'Times New Roman\',serif' in s)
        tip_paragraphs = content_div.find_all('p') if content_div else []
        tip_text = "\n\n".join([p.get_text(strip=True) for p in tip_paragraphs])

        source_div = main_content.find('div', style=lambda s: s and 'font-family:Helvetica Neue,Helvetica,Arial,sans-serif' in s)
        source_text = source_div.get_text(strip=True) if source_div else ""

        return {
            "block_type": "article",
            "title": title_text,
            "body_text": f"{tip_text}\n\nSource: {source_text}",
            "image_url": "",
            "link_url": "",
        }
    return None

# Dorie Clark Processor
def process_dorie_clark(data):
    logger.debug("Processing Dorie Clark newsletter")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Dorie Clark Newsletter")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_blocks = extract_dorie_clark_content(soup)
    output_json['content']['content_blocks'] = content_blocks
    
    return output_json, 200

def extract_dorie_clark_content(soup):
    content_blocks = []
    main_content_div = soup.find('div', class_='message-content')
    if main_content_div:
        content = []
        in_ad_section = False
        ad_counter = 0

        for elem in main_content_div.find_all(['p', 'ul', 'ol', 'h2']):
            text = elem.get_text(strip=True)

            if "***" in text:
                ad_counter += 1
                in_ad_section = ad_counter % 2 != 0
                continue

            if not in_ad_section:
                if elem.name == 'p':
                    content.append(text)
                elif elem.name in ['ul', 'ol']:
                    for li in elem.find_all('li'):
                        content.append(f"- {li.get_text(strip=True)}")

            if text.startswith('PS -'):
                break

        text = '\n\n'.join(content)

        block = {
            "block_type": "article",
            "title": "Dorie Clark's Insights",
            "body_text": text,
            "image_url": "",
            "link_url": "",
        }
        content_blocks.append(block)

    return content_blocks

# Adweek Processor
def process_adweek(data):
    logger.debug("Processing Adweek email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Adweek")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_blocks = extract_adweek_content(soup)
    output_json['content']['content_blocks'] = content_blocks
    
    return output_json, 200

def extract_adweek_content(soup):
    content_blocks = []
    blocks = soup.find_all(['table', 'div'], class_=['em_wrapper'])

    for block in blocks:
        title_elem = block.find(['span', 'td'], class_='em_font_18')
        if title_elem and title_elem.a:
            title = title_elem.a.text.strip()
            link = title_elem.a.get('href', '')

            img_elem = block.find('img', class_='em_full_img')
            image = img_elem['src'] if img_elem else ''

            desc_elem = block.find(['span', 'td'], class_='em_font_15')
            description = desc_elem.text.strip() if desc_elem else ''

            content_block = {
                "block_type": "article",
                "title": title,
                "body_text": description,
                "image_url": image,
                "link_url": link,
            }
            content_blocks.append(content_block)

    return content_blocks

# Campaign Brief Processor
def process_campaign_brief(data):
    logger.debug("Processing Campaign Brief email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Campaign Brief")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_blocks = extract_campaign_brief_content(soup)
    output_json['content']['content_blocks'] = content_blocks
    
    return output_json, 200

def extract_campaign_brief_content(soup):
    content_blocks = []
    rss_column = soup.find('table', id='rssColumn')
    
    if rss_column:
        blocks = rss_column.find_all('div', style=lambda value: value and 'text-align: left;color: #656565;min-width: 300px;' in value)
        
        for block in blocks:
            content = {
                "block_type": "article"
            }

            img_tag = block.find('img', class_='mc-rss-item-img')
            if img_tag:
                content['image_url'] = img_tag.get('src', '')

            headline_tag = block.find('a', style=lambda value: value and "font-family: 'Oswald'" in value)
            if headline_tag:
                content['title'] = headline_tag.text.strip()
                content['link_url'] = headline_tag.get('href', '')

            description_tag = block.find('div', id='rssContent')
            if description_tag:
                content['body_text'] = description_tag.text.strip()

            if content.get('title') and (content.get('image_url') or content.get('link_url')):
                content_blocks.append(content)

    return content_blocks

# Creative Bloq Processor
def process_creative_bloq(data):
    logger.debug("Processing Creative Bloq email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Creative Bloq")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_blocks = extract_creative_bloq_content(soup)
    output_json['content']['content_blocks'] = content_blocks
    
    return output_json, 200

def extract_creative_bloq_content(soup):
    content_blocks = []
    content_tables = soup.find_all('table', class_='name-59')

    for table in content_tables:
        story_blocks = table.find_all('table', class_='name-60')
        
        for story in story_blocks:
            story_data = {
                "block_type": "article"
            }

            headline = story.find('div', attrs={'data-testid': 'copy_headline'})
            if headline:
                story_data['title'] = headline.text.strip()

            additional_text = story.find('div', class_='name-100')
            if additional_text:
                story_data['body_text'] = additional_text.text.strip()

            link = story.find('a', attrs={'data-testid': 'cta_link'})
            if link:
                story_data['link_url'] = link['href']

            img = story.find('img', class_='scale_full_width')
            if img:
                story_data['image_url'] = img['src']

            if story_data.get('title') and (story_data.get('image_url') or story_data.get('link_url')):
                content_blocks.append(story_data)

    return content_blocks

# Generic Processor
def process_generic(data):
    logger.debug("Processing generic email")
    content_html = data['metadata']['content']['html']
    metadata = data['metadata']
    output_json = create_base_output_structure(metadata, "Generic Newsletter")
    
    soup = BeautifulSoup(content_html, 'html.parser')
    content_blocks = extract_generic_content(soup)
    output_json['content']['content_blocks'] = content_blocks
    
    return output_json, 200

def extract_generic_content(soup):
    content_blocks = []
    
    # Extract title
    title = soup.find(['h1', 'h2'])
    title_text = title.text.strip() if title else "Untitled"

    # Extract main content
    main_content = soup.find(['div', 'table'], class_=['content', 'main'])
    if not main_content:
        main_content = soup.find('body')

    content = main_content.get_text(strip=True) if main_content else ""

    # Extract first image
    img = soup.find('img')
    image_url = img['src'] if img and 'src' in img.attrs else ""

    # Extract first link
    link = soup.find('a')
    link_url = link['href'] if link and 'href' in link.attrs else ""

    content_block = {
        "block_type": "article",
        "title": title_text,
        "body_text": content,
        "image_url": image_url,
        "link_url": link_url,
    }
    content_blocks.append(content_block)

    return content_blocks

# Main execution (for testing)
if __name__ == "__main__":
    # This block can be used for testing or running the script directly
    pass