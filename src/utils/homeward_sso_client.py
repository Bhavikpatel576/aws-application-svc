import logging
from typing import functools

import requests
from django.conf import settings
from requests.exceptions import RequestException
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

def sso_resp_to_drf_response(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Response:
        try:
            resp = func(*args, **kwargs)
        except RequestException as e:
            logger.exception(f"Unable to reach homeward-sso/user endpoint", exc_info=e,
                             extra=dict(type='unable_to_reach_sso'))
            return Response({"error": "Unable to complete the request"}, status.HTTP_503_SERVICE_UNAVAILABLE)
        if resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error(f"Homeward SSO returned 500", extra=dict(type='sso_returned_500_error'))
            return Response({"error": "Unable to complete the request"}, status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(resp.json(), resp.status_code)
    return wrapper


class HomewardSSO():
    def __init__(self):
        self.headers = {'Authorization': getattr(settings, 'HOMEWARD_SSO_AUTH_TOKEN')}
        self.user_endpoint = getattr(settings, 'HOMEWARD_SSO_BASE_URL') + 'user/'

    @sso_resp_to_drf_response
    def create_agent_user(self, data):
        return requests.post(self.user_endpoint, data=data, headers=self.headers)

    @sso_resp_to_drf_response
    def update_user_groups(self, data, username):
        url = f"{self.user_endpoint}{username}/groups/add"
        return requests.post(url, json=data, headers=self.headers)
