from unittest import mock

from requests.exceptions import ProxyError
from rest_framework.test import APISimpleTestCase

from blend.blend_api_client import get, BlendClientException

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.reason = None

    def json(self):
        return self.json_data

def mocked_403(type, url, headers, params):
    return MockResponse("Account is Locked", 403)

def mocked_401(type, url, headers, params):
    return MockResponse("Invalid Credentials", 401)

def mocked_get_followups(type, url, headers, params, proxies):
    return MockResponse(None, 200)

class BlendClientTests(APISimpleTestCase):

    @mock.patch('requests.request', side_effect=mocked_403)
    def test_client_failure_403(self, mock_requests_request):
        querystring = {"applicationId": "336f6e2c-6461-4cea-ae31-b176e186904d"}
        with self.assertRaises(BlendClientException, msg="403 Error - check if account is locked out."):
            get('https://call.without.proxy/follow-ups', querystring, 0)

    @mock.patch('requests.request', side_effect=mocked_401)
    def test_client_failure_401(self, mock_requests_request):
        querystring = {"applicationId": "336f6e2c-6461-4cea-ae31-b176e186904d"}
        with self.assertRaises(BlendClientException, msg="401 Error - check credentials."):
            get('https://call.without.proxy/follow-ups', querystring, 0)
    
    @mock.patch('requests.request', side_effect=ProxyError("mocked proxy error"))
    def test_client_proxy_error(self, mock_requests_request):
        querystring = {"applicationId": "336f6e2c-6461-4cea-ae31-b176e186904d"}
        with self.assertRaises(BlendClientException, msg="Proxy Error - retries exceeded"):
            get('https://call.without.proxy/follow-ups', querystring, 0)

    @mock.patch('requests.request', side_effect=[ProxyError("mocked proxy error"), MockResponse(None, 200)])
    def test_client_retries_when_proxy_error_received(self, mock_requests_request):
        querystring = {"applicationId": "336f6e2c-6461-4cea-ae31-b176e186904d"}
        get('https://api.blendlabs.com/follow-ups', querystring, 0)
        self.assertEqual(mock_requests_request.call_count, 2)

    @mock.patch('requests.request', side_effect=[ProxyError("mocked proxy error"), ProxyError("mocked proxy error")])
    def test_client_exception_thrown_when_retries_exceed(self, mock_requests_request):
        querystring = {"applicationId": "336f6e2c-6461-4cea-ae31-b176e186904d"}
        with self.assertRaises(BlendClientException, msg='Proxy Error - retries exceeded'):
            get('https://api.blendlabs.com/follow-ups', querystring, 3)

    @mock.patch('requests.request', side_effect=mocked_get_followups)
    def test_client_success(self, mock_requests_request):
        querystring = {"applicationId": "336f6e2c-6461-4cea-ae31-b176e186904d"}
        resp = get('https://api.blendlabs.com/follow-ups', querystring, 0)
        self.assertEqual(resp.status_code, 200)