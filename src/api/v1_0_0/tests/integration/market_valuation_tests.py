"""
Test cases for Market valuation flow.
"""

from rest_framework import status
from rest_framework.test import APITestCase

from api.v1_0_0.tests._utils.data_generators import get_fake_market_valuation
from api.v1_0_0.tests.integration.mixins import AuthMixin


class MarketValuationTestCase(AuthMixin, APITestCase):
    """
    Test case class for Market valuation flow.
    """

    def test_market_valuation_post(self):
        """
        Test case to test POST call.
        """

        # Test without login.
        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with valid data and valid login user
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test with invalid data
        invalid_data = {
            "value_opinions": [
                {
                    "comments": [
                        {
                            "is_favorite": True,  # 'comment' field is required.
                        }
                    ]
                }
            ]
        }

        response = self.client.post(url, invalid_data, **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_market_valuation_post_as_user(self):
        """
        Test case to test POST call.
        """

        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)

        token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_market_valuation_retrieve(self):
        """
        Test case to test retrieve (GET) operation of market valuation.
        """

        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()

        # Test without login.
        retrieve_url = "{}{}/".format(url, market_valuation['current_home'])
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with login.
        response = self.client.get(retrieve_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_market_valuation_retrieve_as_user(self):
        """
        Test case to test retrieve (GET) operation of market valuation.
        """

        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()

        user_token = self.create_and_login_user('fakeloginuser')
        user_headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(user_token)
        }

        retrieve_url = "{}{}/".format(url, market_valuation['current_home'])
        response = self.client.get(retrieve_url, **user_headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_market_valuation_patch(self):
        """
        Test case to test update on market valuation
        """

        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()

        valid_data = {'id': market_valuation['id'], 'property_condition': 'Average', 'is_built_after_1960': False,
                      'avm': [{'name': 'House Canary', 'link': 'http://link1.com'}],
                      'value_opinions': [
                          {'id': market_valuation['value_opinions'][0]['id'], 'suggested_list_price': 400000,
                           'type': 'sr_analyst',
                           'comments': [{'id': market_valuation['value_opinions'][0]['comments'][0]['id'],
                                         'is_favorite': False}]}],
                      'comparables': [{'id': market_valuation['comparables'][0]['id'], 'comparable_type': 'Secondary',
                                       'address': {'city': 'Test_city'}}]}

        invalid_data = {'id': market_valuation['id'], 'is_less_than_one_acre': 'abc',
                        'avm': [{'name': 'something'}], 'value_opinions': [{'type': 'super',
                                                                            'comments': [{'is_favorite': "xyz"}]}]}

        # Test without login.
        retrieve_url = "{}{}/".format(url, market_valuation['current_home'])
        response = self.client.patch(retrieve_url, valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with login with valid data.
        response = self.client.patch(retrieve_url, valid_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test with login with invalid data.
        response = self.client.patch(retrieve_url, invalid_data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_market_valuation_patch_as_user(self):
        """
        Test case to test update on market valuation
        """

        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        user_token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        user_headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(user_token)
        }
        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()

        valid_data = {
            'id': market_valuation['id'],
            'property_condition': 'Average',
            'is_built_after_1960': False,
            'avm': [
                {
                    'name': 'House Canary',
                    'link': 'http://link1.com'
                }
            ],
            'value_opinions': [
                {
                    'id': market_valuation['value_opinions'][0]['id'],
                    'suggested_list_price': 400000,
                    'type': 'sr_analyst',
                    'comments': [
                        {
                            'id': market_valuation['value_opinions'][0]['comments'][0]['id'],
                            'is_favorite': False
                        }
                    ]
                }
            ],
            'comparables': [
                {
                    'id': market_valuation['comparables'][0]['id'],
                    'comparable_type': 'Secondary',
                    'address': {
                        'city': 'Test_city'
                    }
                }
            ]
        }

        retrieve_url = "{}{}/".format(url, market_valuation['current_home'])

        response = self.client.patch(retrieve_url, valid_data, **user_headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_market_value_opinion_comment_delete(self):
        """
        Test case to test delete on market value opinion comment
        """

        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()

        # Test without login
        required_url = "{}{}/".format('/api/1.0.0/market-value-opinion-comment/', market_valuation['value_opinions'][0]['comments'][0]['id'])
        response = self.client.delete(required_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with login
        required_url = "{}{}/".format('/api/1.0.0/market-value-opinion-comment/', market_valuation['value_opinions'][0]['comments'][0]['id'])
        response = self.client.delete(required_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_comparable_delete(self):
        """
        Testcase to test delete on comparable.
        """

        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()

        # Test without login
        required_url = "{}{}/".format('/api/1.0.0/comparable/', market_valuation['comparables'][0]['id'])
        response = self.client.delete(required_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with login
        required_url = "{}{}/".format('/api/1.0.0/comparable/', market_valuation['comparables'][0]['id'])
        response = self.client.delete(required_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_comparable_delete_as_user(self):
        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        user_token = self.create_and_login_user('fakeloginuser')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        user_headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(user_token)
        }

        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()

        required_url = "{}{}/".format('/api/1.0.0/comparable/', market_valuation['comparables'][0]['id'])
        response = self.client.delete(required_url, **user_headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_min_price_max_price(self):
        """
        """
        url = '/api/1.0.0/market-valuation/'
        application = self.create_application('fakeapplication')
        data = get_fake_market_valuation(application.current_home_id)
        token = self.create_and_login_admin('fakeloginadmin')
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }
        response = self.client.post(url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        market_valuation = response.json()
        data = {
            "current_home": market_valuation['current_home'],
            "property_condition": "Excellent",
            "is_less_than_one_acre": "",
            "is_in_completed_neighborhood": "",
            "is_built_after_1960": "",
            "comparables": [],
            "value_opinions": [
                {
                    "id": market_valuation['value_opinions'][0]['id'],
                    "minimum_sales_price": "11",
                    "maximum_sales_price": "11",
                    "type": "local_agent",
                    "comments": []
                }
            ]
        }
        retrieve_url = "{}{}/".format(url, market_valuation['current_home'])

        # for equal prices
        response = self.client.patch(retrieve_url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['value_opinions'][0]['minimum_sales_price'][0], 'Values must be different')

        # for max price less than min price
        data['value_opinions'][0]['maximum_sales_price'] = '1'
        response = self.client.patch(retrieve_url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['value_opinions'][0]['maximum_sales_price'][0], 'Max value must be higher than min value')

        data['value_opinions'][0]['maximum_sales_price'] = '12'
        response = self.client.patch(retrieve_url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # for min price greater than max price
        data['value_opinions'][0]['minimum_sales_price'] = '150'
        response = self.client.patch(retrieve_url, data, **headers, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['value_opinions'][0]['minimum_sales_price'][0], 'Min value must be lower than max value')
