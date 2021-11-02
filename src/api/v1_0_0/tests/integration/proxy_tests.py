from json import JSONDecodeError
import json
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from .mixins import AuthMixin

from api.v1_0_0.tests._utils.data_generators import BaseMockedOKRequestsResponse

User = get_user_model()

class MockHomewardSSOService:
    success_data = {
        "id": 12345,
        "groups": ["test"],
        "services": [],
        "last_login": "2021-09-30T21:57:55.040720Z",
        "is_superuser": False,
        "email": "test1@gmail.com",
        "is_staff": False,
        "is_active": True,
        "date_joined": "2021-09-30T21:57:54.929709Z",
        "first_name": "fn",
        "last_name": "ln",
        "calendar_link": None,
        "user_permissions": []
    }
    existing_email_data = {"email":["user with this email address already exists."]}

    def __init__(self):
        self.create_agent_user = MagicMock(side_effect=self.create_agent_user_side_effect)
        self.update_user_groups = MagicMock(side_effect=self.update_user_groups_side_effect)

    def create_agent_user_side_effect(self, data):
        if data.get("email") == "existinguser@email.com":
            return Response(self.existing_email_data, status=400)
        return Response(self.success_data, status=201)

    def update_user_groups_side_effect(self, data, username):
        return Response(None, 200)


def mocked_hw_sso_resend_verify_email_call(url, json, headers):
    if json.get('email') == 'success@verifyemail.com':
        return Response(None, 200)
    return Response(None, 400)


class CreateAgentTests(APITestCase):
    def setUp(self):
        self.proxy_url = "/api/1.0.0/proxy/agents/"

    @patch("api.v1_0_0.views.proxy_views.HomewardSSO", return_value=MockHomewardSSOService())
    def test_new_user(self, sso_service_mock):
        data = {
            "email": "newuser@email.com",
            "password": "password",
            "first_name": "first",
            "last_name": "last",
        }
        resp = self.client.post(self.proxy_url, data, format="json")
        data["group"] = "Claimed Agent"
        self.assertEqual(resp.status_code, 201)
        sso_service_mock.return_value.create_agent_user.assert_called_with(data=data)


    @patch("api.v1_0_0.views.proxy_views.HomewardSSO", return_value=MockHomewardSSOService())
    def test_existing_user(self, sso_service_mock):
        data = {
            'email': 'existinguser@email.com',
            'password': 'password',
            'first_name': 'first',
            'last_name': 'last'
        }

        resp = self.client.post(self.proxy_url, data, format='json')
        data["group"] = "Claimed Agent"
        sso_service_mock.return_value.create_agent_user.assert_called_with(data=data)
        self.assertEqual(resp.status_code, 400)


class AddUserToCasGroupsTests(AuthMixin, APITestCase):
    def setUp(self):
        self.headers = {'Authorization': getattr(settings, 'HOMEWARD_SSO_AUTH_TOKEN', '')}
        self.expected_headers = "headers={}".format(self.headers)
        self.token = self.create_and_login_user('fake_logged_in_user')
        self.url = '/api/1.0.0/user/groups/add'
        self.headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)
        }


    def test_add_user_to_group(self):
        payload = {"groups": ["Claimed Agent"]}

        with patch('src.api.v1_0_0.views.proxy_views.requests.post') as m:
            m.return_value = BaseMockedOKRequestsResponse()
            response = self.client.post(self.url, payload, **self.headers, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            m.assert_called_once()

    def test_add_user_to_groups(self):
        payload = {"groups": ["Claimed Agent", "Customer"]}

        with patch('src.api.v1_0_0.views.proxy_views.requests.post') as m:
            m.return_value = BaseMockedOKRequestsResponse()
            response = self.client.post(self.url, payload, **self.headers, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            m.assert_called_once()


    def test_add_user_to_bad_groups(self):
        bad_groups = ["Verified Email", "claimed agent", "customer", "blah"]
        payload = {"groups": bad_groups}
        with patch('src.api.v1_0_0.views.proxy_views.requests.post') as m:
            m.return_value = BaseMockedOKRequestsResponse()
            response = self.client.post(self.url, payload, **self.headers, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            m.assert_not_called()
            for bad_group in bad_groups:
                self.assertIn(bad_group, response.json())


    def test_add_user_to_group_bad_token_fails(self):
        headers = {'HTTP_AUTHORIZATION': 'Token Bad'}
        payload = {"groups": ["Claimed Agent"]}
        with patch('src.api.v1_0_0.views.proxy_views.requests.post') as m:
            m.return_value = BaseMockedOKRequestsResponse()
            response = self.client.post(self.url, payload, **headers, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            m.assert_not_called()


class ResendVerifyEmailTests(APITestCase):
    def setUp(self):
        self.headers = {'Authorization': getattr(settings, 'HOMEWARD_SSO_AUTH_TOKEN', '')}
        self.expected_headers = "headers={}".format(self.headers)
        self.url = '/api/1.0.0/proxy/resend-verify-email/'

    @patch('requests.post', side_effect=mocked_hw_sso_resend_verify_email_call)
    def test_proxy_resend_verify_email(self, mock):
        payload = {"email": "success@verifyemail.com"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertRegex(str(mock.call_args_list[0]), self.expected_headers)

    @patch('requests.post', side_effect=mocked_hw_sso_resend_verify_email_call)
    def test_proxy_resend_verify_email(self, mock):
        payload = {"email": "fail@verifyemail.com"}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRegex(str(mock.call_args_list[0]), self.expected_headers)