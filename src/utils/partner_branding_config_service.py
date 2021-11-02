import logging

from django.conf import settings
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
from rest_framework import serializers


logger = logging.getLogger(__name__)


def get_partner(slug):
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=3
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    response = http.get(f'{settings.PARTNER_BRANDING_CONFIG_URL}partners/{slug}/cms-config/')
    if response.status_code == 200:
        return json.loads(response.content)['items'][0]
    else:
        logger.error(f"Partner Branding Service returned {response.status_code} with message {response.reason}")
        return {}