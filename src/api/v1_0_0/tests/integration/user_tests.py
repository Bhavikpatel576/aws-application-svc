from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from api.v1_0_0.tests._utils.data_generators import get_custom_view
from api.v1_0_0.tests.integration.mixins import AuthMixin

from application.models.customer import Customer
from application.models.application import Application
from application.models.real_estate_agent import RealEstateAgent
from application.tests import random_objects

from api.v1_0_0.tests._utils import data_generators


class UserTestCase(AuthMixin, APITestCase):

    def test_me_view(self):
        """
        test me view
        """
        url = '/api/1.0.0/user/me'
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            response = self.client.get(url, **headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['username'], "usernamefakeloginuser")
            self.assertListEqual(response.data["groups"], ["Verified Email", "Claimed Agent"])

    def test_me_view_no_groups(self):
        """
        test me view
        """
        url = '/api/1.0.0/user/me'
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedNoGroupsUserReponse()
            response = self.client.get(url, **headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['username'], "usernamefakeloginuser")
            self.assertListEqual(response.data["groups"], [])

    def test_user_logout(self):
        """
        test user logout
        """
        url = '/api/1.0.0/cas/logout'
        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_user_custom_view(self):
        """
        test list user custom view
        """
        url = '/api/1.0.0/user/custom-view/'
        user = self.create_user('fakeloginuser')
        self.create_user_custom_view('fake_custom_view', user)
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }

        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['results'][0]['name'], 'fake_custom_view')

    def test_create_user_custom_view(self):
        """
        """
        url = '/api/1.0.0/user/custom-view/'
        token = self.create_and_login_user('fakeloginuser')
        custom_view = get_custom_view('fake_custom_view')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, custom_view, **headers)
        self.assertEqual(response.status_code,
                         status.HTTP_201_CREATED)
        self.assertEqual(
            response.json()['name'], 'fake_custom_view')

    def test_update_user_custom_view(self):
        """
        """
        url = '/api/1.0.0/user/custom-view/'
        user = self.create_user('fakeloginuser')
        custom_view = self.create_user_custom_view('fake_custom_view', user)
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }
        data = {
            "name": 'new_custom_view'
        }
        response = self.client.patch("{}{}/".format(url, custom_view.id), data, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['name'], 'new_custom_view')

    def test_get_loan_for_application_without_loan(self):
        url = '/api/1.0.0/user/application/active/'
        user = self.create_user('fakeloginuser')
        c = Customer.objects.create(name='Test User', email=user.email)
        agent_user = self.create_user("fake_agent_user1")
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=agent_user.email))
        Application.objects.create(customer=c, **data_generators.get_fake_application("agent", buying_agent=agent))
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['loan'], {})

    def test_get_loan_for_application_with_loan(self):
        url = '/api/1.0.0/user/application/active/'
        user = self.create_user('fakeloginuser')
        c = Customer.objects.create(name='Test User', email=user.email)
        agent_user = self.create_user("fake_agent_user1")
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=agent_user.email))
        application_1 = Application.objects.create(customer=c,**data_generators.get_fake_application("agent",
                                                                                                      buying_agent=agent))
        loan = random_objects.random_loan(application=application_1,
                                          blend_application_id='000f6e2c-6461-4cea-ae31-b176e1869000',
                                          salesforce_id='3')
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.json()['loan'])

    def test_get_loan_for_application_with_multiple_loans(self):
        url = '/api/1.0.0/user/application/active/'
        user = self.create_user('fakeloginuser')
        c = Customer.objects.create(name='Test User', email=user.email)
        agent_user = self.create_user("fake_agent_user1")
        agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=agent_user.email))
        application_1 = Application.objects.create(customer=c, **data_generators.get_fake_application("agent",
                                                                                                      buying_agent=agent))
        loan = random_objects.random_loan(application=application_1,
                                          blend_application_id='000f6e2c-6461-4cea-ae31-b176e1869000',
                                          salesforce_id='3')
        loan.status = 'Withdrawn'
        loan.save()

        loan2 = random_objects.random_loan(application=application_1,
                                           blend_application_id='000f6e2c-6461-4cea-ae31-c176e1869000',
                                           salesforce_id='4')
        token = self.login_user(user)
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token[1])
        }
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['loan']['id'], str(loan2.id))
