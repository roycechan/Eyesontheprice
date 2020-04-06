import tldextract
import urllib
from urllib.parse import urlparse
import requests
import re

SHOPEE_SEARCH_LINK = "https://shopee.sg/api/v2/item/get?"

def extract_url(text):
    finder = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    url_list = finder.findall(text)
    return url_list


def extract_domain(url):
    extracted = tldextract.extract(url)
    return extracted.domain





def build_search_url(url, parameters):
    final_url = url + urllib.parse.urlencode(parameters)
    return final_url


def retrieve_item_details_json(url):
    headers = {
        'User-Agent': 'Mozilla/5',
    }

    r = requests.get(url, headers=headers).json()
    return r

