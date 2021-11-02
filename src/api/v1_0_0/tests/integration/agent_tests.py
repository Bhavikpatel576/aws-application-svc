"""
/agent/<sf_id> test cases.
"""
from unittest.mock import patch
from uuid import UUID

from rest_framework.test import APITestCase

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.real_estate_agent import RealEstateAgent
from application.tests import random_objects
from application.tests.random_objects import random_agent

""" test has unit tests that need to be seperated out """
class AgentTests(AuthMixin, APITestCase):
    def test_update_agent(self):
        sf_id = "0013C00000GG3XjQAL"
        inital_agent = {
            "sf_id": sf_id,
            "name": "Brandon Kirchner",
            "phone": "512-512-5124",
            "email": "brandon+dsfmgklaetrjg@homeward.com",
            "company": "brandons brokerage",
            "is_certified": True
        }
        RealEstateAgent.objects.create(**inital_agent)
        url = '/api/1.0.0/agent/{}/'.format(sf_id)
        token = self.create_and_login_admin('fakeloginadmin')
        data = {
            "name": "Not Brandon",
            "phone": "123-123-1231",
            "email": "notbrandon+dsfmgklaetrjg@homeward.com",
            "company": "not brandons brokerage",
            "is_certified": True
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.put(url, data, **headers, format='json')
        certified_agent = RealEstateAgent.objects.get(sf_id=sf_id)
        self.assertEqual(certified_agent.name, data.get('name'))
        self.assertEqual(resp.status_code, 200)

    def test_upsert_agent(self):
        sf_id = "0013C00000GG3XjQAL"
        url = '/api/1.0.0/agent/{}/'.format(sf_id)
        token = self.create_and_login_admin('fakeloginadmin')

        brokerage = random_objects.random_brokerage(sf_id='0013C00000GG3XjQAM')
        data = {
            "sf_id": "0013C00000GG3XjQAL",
            "name": "Brandon Kirchner",
            "phone": "512-512-5124",
            "email": "brandon+dsfmgklaetrjg@homeward.com",
            "company": "brandons brokerage",
            "is_certified": True,
            "brokerage_sf_id": brokerage.sf_id
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.put(url, data, **headers, format='json')

        certified_agent = RealEstateAgent.objects.get(sf_id=data.get('sf_id'))
        self.assertEqual(certified_agent.name, data.get('name'))
        self.assertEqual(certified_agent.brokerage.id, brokerage.id)
        self.assertEqual(resp.status_code, 201)

    @patch('api.v1_0_0.serializers.agent_serializers.homeward_salesforce.get_account_by_id')
    def test_upsert_agent_with_new_brokerage(self, sf_patch):
        sf_patch.return_value = {
            'Name': 'Brandons Brokerage',
            'Broker_Partnership_Status__c': 'Partnership launched',
            'Id': '0013C00000GG3XjQAL'
        }

        sf_id = "0013C00000GG3XjQAL"
        url = '/api/1.0.0/agent/{}/'.format(sf_id)
        token = self.create_and_login_admin('fakeloginadmin')

        brokerage_sf_id = '0013C00000GG3XjQAM'
        data = {
            "sf_id": "0013C00000GG3XjQAL",
            "name": "Brandon Kirchner",
            "phone": "512-512-5124",
            "email": "brandon+dsfmgklaetrjg@homeward.com",
            "company": "brandons brokerage",
            "is_certified": True,
            "brokerage_sf_id": brokerage_sf_id
        }
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.put(url, data, **headers, format='json')

        certified_agent = RealEstateAgent.objects.get(sf_id=data.get('sf_id'))
        self.assertEqual(certified_agent.name, data.get('name'))
        self.assertEqual(certified_agent.brokerage.sf_id, brokerage_sf_id)
        self.assertEqual(resp.status_code, 201)

    def test_delete_agent(self):
        sf_id = "0013C00000GG3XjQAL"
        inital_agent = {
            "sf_id": sf_id,
            "name": "Brandon Kirchner",
            "phone": "512-512-5124",
            "email": "brandon+dsfmgklaetrjg@homeward.com",
            "company": "brandons brokerage",
            "is_certified": True
        }
        RealEstateAgent.objects.create(**inital_agent)
        url = '/api/1.0.0/agent/{}/'.format(sf_id)
        token = self.create_and_login_admin('fakeloginadmin')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        resp = self.client.delete(url, '', **headers, format='json')

        with self.assertRaises(RealEstateAgent.DoesNotExist):
            RealEstateAgent.objects.get(sf_id=sf_id)
        self.assertEqual(resp.status_code, 204)

    def test_get_certified_agent(self):
        agent = {
            "sf_id": "0013C00000GG3XjQAL",
            "name": "Brandon Kirchner",
            "phone": "512-512-5124",
            "email": "brandon+dsfmgklaetrjg@homeward.com",
            "company": "brandons brokerage",
            "self_reported_referral_source": "something",
            "self_reported_referral_source_detail": "something else",
            "is_certified": True
        }

        agent_obj = RealEstateAgent.objects.create(**agent)
        url = '/api/1.0.0/certified-agent/{}/'.format(agent_obj.pk)
        resp = self.client.get(url)
        self.assertEqual(resp.data["name"], agent["name"])
        self.assertEqual(resp.data["phone"], "(512) 512-5124")
        self.assertEqual(resp.data["email"], agent["email"])
        self.assertEqual(resp.data["company"], agent["company"])
        self.assertEqual(resp.data["id"], str(agent_obj.id))

        agent["is_certified"] = False
        agent['sf_id'] = None
        agent_obj_not_certified = RealEstateAgent.objects.create(**agent)
        url = '/api/1.0.0/certified-agent/{}/'.format(agent_obj_not_certified.pk)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_prefer_certified_get_agent_by_email(self):
        brokerage = random_objects.random_brokerage()
        agent = random_agent(is_certified=True, sf_id='blah', brokerage=brokerage)

        # create a second agent w/ the same phone and email
        RealEstateAgent.objects.create(name=agent.name, phone=agent.phone, email=agent.email)

        url = '/api/1.0.0/agent/lookup/?email={}&phone={}'.format(agent.email, agent.phone)

        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(UUID(resp.data['id']), agent.id)
        self.assertEqual(resp.data['name'], agent.name)
        self.assertEqual(resp.data['phone'], agent.phone)
        self.assertEqual(resp.data['email'], agent.email)
        self.assertEqual(resp.data['is_certified'], agent.is_certified)

        self.assertEqual(resp.data['brokerage']['name'], agent.brokerage.name)
        self.assertEqual(UUID(resp.data['brokerage']['id']), agent.brokerage.id)
        self.assertEqual(resp.data['brokerage'].get('sf_id'), None)

    def test_get_agent_by_email(self):
        brokerage = random_objects.random_brokerage()
        agent = random_agent(is_certified=True, sf_id='blah', brokerage=brokerage)
        url = '/api/1.0.0/agent/lookup/?email={}'.format(agent.email)

        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['name'], agent.name)
        self.assertEqual(resp.data['phone'], agent.phone)
        self.assertEqual(resp.data['email'], agent.email)
        self.assertEqual(resp.data['is_certified'], agent.is_certified)

        self.assertEqual(resp.data['brokerage']['name'], agent.brokerage.name)
        self.assertEqual(UUID(resp.data['brokerage']['id']), agent.brokerage.id)
        self.assertEqual(resp.data['brokerage'].get('sf_id'), None)

    def test_get_agent_by_phone(self):
        brokerage = random_objects.random_brokerage(logo_url='http://www.cats.com/cat.jpg')
        agent = random_agent(is_certified=True, sf_id='blah', brokerage=brokerage)
        url = '/api/1.0.0/agent/lookup/?email={}&phone={}'.format("fake-email@gmail.com", agent.phone)

        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['name'], agent.name)
        self.assertEqual(resp.data['phone'], agent.phone)
        self.assertEqual(resp.data['email'], agent.email)
        self.assertEqual(resp.data['is_certified'], agent.is_certified)

        self.assertEqual(resp.data['brokerage']['name'], agent.brokerage.name)
        self.assertEqual(UUID(resp.data['brokerage']['id']), agent.brokerage.id)
        self.assertEqual(resp.data['brokerage'].get('sf_id'), None)
        self.assertEqual(resp.data['brokerage']['logo_url'], 'http://www.cats.com/cat.jpg')

    def test_get_agent_by_email_or_phone_will_204(self):
        url = '/api/1.0.0/agent/lookup/?email={}&phone={}'.format("fake-email@gmail.com", '5129235534')

        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 204)
