
from utils.homeward_sso_client import HomewardSSO
from unittest.mock import patch, ANY
from django.conf import settings
from rest_framework.test import APISimpleTestCase

def mocked_create_agent_post(url, data, headers):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if data.get('email') == 'newuser@email.com':
        return MockResponse(None, 201)
    elif data.get('email') == 'existinguser@email.com':
        return MockResponse(None, 400)
    elif data.get('email') == 'servererror@email.com':
        return MockResponse(None, 500)
    return MockResponse(None, 404)

def mocked_hw_sso_resend_verify_email_call(url, json, headers):
    class MockResponse:
        def __init__(self, status):
            self.status_code = status

    if json.get('email') == 'success@verifyemail.com':
        return MockResponse(200)
    return MockResponse(400)


class HomewardSSOClientTests(APISimpleTestCase):
    def setUp(self):
        self.headers = {'Authorization': getattr(settings, 'HOMEWARD_SSO_AUTH_TOKEN', '')}
        self.expected_headers = "headers={}".format(self.headers)
        self.user_endpoint = getattr(settings, 'HOMEWARD_SSO_BASE_URL', 'http://localhost:8000/') + 'user/'

    def test_sso_happy_path(self):
        with patch('requests.post') as mock_post:
            mock_post.side_effect = mocked_create_agent_post
            data = {
                'email': 'newuser@email.com',
                'password': 'password',
                'first_name': 'first',
                'last_name': 'last',
                'group': 'Claimed Agent'
            }

            resp = HomewardSSO().create_agent_user(data)
            self.assertEqual(resp.status_code, 201)
            mock_post.assert_called_with('user/', data=data, headers=ANY)
            self.assertRegex(str(mock_post.call_args_list[0]), self.expected_headers)

    def test_sso_email_exists(self):
        with patch('requests.post') as mock_post:
            mock_post.side_effect = mocked_create_agent_post
            data = {
                'email': 'existinguser@email.com',
                'password': 'password',
                'first_name': 'first',
                'last_name': 'last',
                'group': 'Claimed Agent'
            }

            resp = HomewardSSO().create_agent_user(data)
            self.assertEqual(resp.status_code, 400)
            mock_post.assert_called_with('user/', data=data, headers=ANY)
            self.assertRegex(str(mock_post.call_args_list[0]), self.expected_headers)

    def test_sso_server_error(self):
        with patch('requests.post') as mock_post:
            mock_post.side_effect = mocked_create_agent_post
            data = {
                'email': 'servererror@email.com',
                'password': 'password',
                'first_name': 'first',
                'last_name': 'last',
                'group': 'Claimed Agent'
            }

            resp = HomewardSSO().create_agent_user(data)
            self.assertEqual(resp.status_code, 503)
            mock_post.assert_called_with('user/', data=data, headers=ANY)
