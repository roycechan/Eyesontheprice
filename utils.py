import tldextract
import urllib
from urllib.parse import urlparse
import requests

SHOPEE_SEARCH_LINK = "https://shopee.sg/api/v2/item/get?"

def extract_domain(url):
    extracted = tldextract.extract(url)
    return extracted.domain


def extract_shopee_identifiers(url):
    product_path = urlparse(url).path.split('.')
    parameters = {}
    parameters['itemid'] = product_path[-1]
    parameters['shopid'] = product_path[-2]
    return parameters


def build_url(url, parameters):
    final_url = url + urllib.parse.urlencode(parameters)
    return final_url


def retrieve_item_details_json(url):
    headers = {
        'User-Agent': 'Mozilla/5',
    }

    r = requests.get(url, headers=headers).json()
    return r