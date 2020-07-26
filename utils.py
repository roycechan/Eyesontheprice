import tldextract
import urllib
from urllib.parse import urlparse
import requests
import re
import logging
import shopee_utils
from bitlyshortener import Shortener
import credentials
from datetime import datetime
import sys

# Enable logging
logging.basicConfig(filename="logs",
                        filemode='a',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

logger = logging.getLogger(__name__)

SHOPEE_SEARCH_LINK = "https://shopee.sg/api/v2/item/get?"


def extract_url(update, context):

    user = context.chat_data['user']

    if update.message.photo:
        # Extract caption
        text = update.message.caption
        logger.info(f"{user.first_name} pasted photo with caption: {text}")
    else:
        text = update.message.text
        logger.info(f"{user.first_name} pasted text: {text}")

    finder = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    url_list = finder.findall(text)

    try:
        return url_list[0]
    except IndexError:
        return None


def extract_domain(url):
    extracted = tldextract.extract(url)
    return extracted.domain


def get_item_information(channel, search_url):
    if channel == "shopee":
        item_json = shopee_utils.get_shopee_json(search_url)
        item_dict, variants_dict, variants_display_dict = shopee_utils.get_shopee_variants(item_json)
        logger.info(f"Bot found item: {item_dict['item_name']} with variants: {variants_display_dict}")
        return item_dict, variants_dict, variants_display_dict


def build_search_url(url, parameters):
    final_url = url + urllib.parse.urlencode(parameters)
    return final_url


def retrieve_item_details_json(url):
    headers = {
        'User-Agent': 'Mozilla/5',
    }

    r = requests.get(url, headers=headers).json()
    return r


def parse_threshold(choice):
    if "update" not in choice:
        # extract number X from string with X%
        threshold = -int(choice.split()[-1].split('%')[0])
        return threshold
    else:
        return -100


def shorten_url(long_urls):
    shortener = Shortener(tokens=credentials.BITLY_TOKENS, max_cache_size=8192)
    urls = shortener.shorten_urls(long_urls)
    return urls


def get_current_date():
    current_date = datetime.date(datetime.now())
    return current_date
