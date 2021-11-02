"""
Blend API Client handles setting up the headers and proxy for making calls to Blend API.
"""

import logging
import requests
import re
import time
from django.conf import settings

logger = logging.getLogger(__name__)

token = settings.BLEND.get('API_KEY')
version = settings.BLEND.get('API_VERSION')
instance = settings.BLEND.get('TARGET_INSTANCE')
max_retries = settings.BLEND.get('BLEND_MAX_RETRIES')

headers = {
    'Blend-API-Version': version,
    'blend-target-instance': instance,
    'Authorization': f'Basic {token}',
    'cache-control': 'no-cache',
    'Content-Type': 'application/json',
}

proxies = {
    "http": "http://localhost:8080",
    "https": "http://localhost:8080"
}


class BlendClientException(Exception):
    pass


def get(url: str, querystring: str, retries: int):    
    retry_counter = retries
    max_retries_int = int(max_retries)
    try:
        response = format_request(url, querystring)
        logger.info("Received response from blend API client", extra=dict(
            type="response_from_blend_api_client",
            request_message=format_message(url),
            retries=retry_counter,
            status_code=response.status_code,
            reason=response.reason,
            response=response.json()
        ))
        if response.status_code == 403:
            raise BlendClientException("403 Error - check if account is locked out.")
        if response.status_code == 401:
            raise BlendClientException("401 Error - check credentials.")
    except requests.exceptions.ProxyError as e:
        if retry_counter < max_retries_int:
            retries = retry_counter + 1 
            time.sleep(retries)
            response = get(url, querystring, retries)
        else: 
            raise BlendClientException("Proxy Error - retries exceeded")
        
    return response

def request_with_proxy(url):
    m = re.search('https?://([A-Za-z_0-9.-]+).*', url)
    return m.group(1) == 'api.blendlabs.com'

def format_request(url, querystring):
    if request_with_proxy(url):
        return requests.request("GET", url, headers=headers, params=querystring, proxies=proxies)
    else: 
        return requests.request("GET", url, headers=headers, params=querystring)

def format_message(url):
    return "withproxy" if request_with_proxy(url) else "withoutproxy"