from rest_framework.test import APITestCase

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.brokerage import Brokerage
from application.tests import random_objects


class BrokerageTests(AuthMixin, APITestCase):
    def test_create_brokerage(self):
        sf_id = '0014P00002M67TNQAZ'
        url = '/api/1.0.0/brokerage/{}/'.format(sf_id)
        token = self.create_and_login_admin('fakeloginadmin')

        brokerage_data = {
            "name": "realty austin",
            "partnership_status": "Partnership Launched",
            "sf_id": sf_id
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.put(url, brokerage_data, **headers, format='json')
        brokerage = Brokerage.objects.get(sf_id=sf_id)

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(brokerage.name, brokerage_data['name'])
        self.assertEqual(brokerage.partnership_status, brokerage_data['partnership_status'])

    def test_update_brokerage(self):
        sf_id = '0014P00002M67TNQAZ'
        url = '/api/1.0.0/brokerage/{}/'.format(sf_id)
        token = self.create_and_login_admin('fakeloginadmin')

        random_objects.random_brokerage(sf_id=sf_id)

        brokerage_data = {
            "name": "realty austin",
            "partnership_status": "Partnership Launched",
            "sf_id": sf_id
        }

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.put(url, brokerage_data, **headers, format='json')

        brokerage = Brokerage.objects.get(sf_id=sf_id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(brokerage.name, brokerage_data['name'])
        self.assertEqual(brokerage.partnership_status, brokerage_data['partnership_status'])
