from unittest.mock import patch

from rest_framework.test import APITestCase

from api.v1_0_0.tests._utils import data_generators
from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.acknowledgement import Acknowledgement
from application.models.disclosure import Disclosure
from application.models.real_estate_agent import RealEstateAgent
from application.tests import random_objects


""" File looks like a mix of unit and integation tests"""
class AgentAcknowledgmentTests(AuthMixin, APITestCase):
    def setUp(self):
        self.user = self.create_user("fake_agent_user1")
        self.token = self.login_user(self.user)[1]
        self.headers = {
                'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)
        }
        self.agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent",
                                                                                                 email=self.user.email))
        self.application = random_objects.random_application()
        self.application.buying_agent = self.agent
        self.application.save()

        self.document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        self.inactive_document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=False)
        self.unacknowledged_acknowledgement = Acknowledgement.objects.create(application=self.application,
                                                                             disclosure=self.document)
        self.acknowledged_acknowledgement = Acknowledgement.objects.create(application=self.application,
                                                                           disclosure=self.document,
                                                                           is_acknowledged=True)
        self.acknowledged_inactive_acknowledgement = Acknowledgement.objects.create(application=self.application,
                                                                           disclosure=self.inactive_document,
                                                                           is_acknowledged=True)

    def test_will_return_acknowledged_acknowledgements_if_agent_is_buying_agent(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            url = f'/api/1.0.0/agent-user/applications/{self.application.id}/acknowledgements/'
            
            response = self.client.get(url, **self.headers, format='json')
            response_json = response.json()
    
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response_json), 1)

            self.assertEqual(response_json[0].get('disclosure').get('id'), str(self.document.id))
            self.assertEqual(response_json[0].get('disclosure').get('name'), self.document.name)

    def test_will_not_return_acknowledgements_if_agent_is_not_buying_agent(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            another_user = self.create_user("fake_agent_user2")
            another_token = self.login_user(another_user)[1]
            new_headers = {
                'HTTP_AUTHORIZATION': 'Token {}'.format(another_token)
            }
            agent2 = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent",
                                                                                                 email=another_user.email))
            agent2.email = agent2.email.upper()
            agent2.save()
            url = f'/api/1.0.0/agent-user/applications/{self.application.id}/acknowledgements/'

            response = self.client.get(url, **new_headers, format='json')
            response_json = response.json()

            self.assertEqual(response.status_code, 404)

    def test_agent_acknowledgment_endpoint_without_login(self): 
        url = f'/api/1.0.0/agent-user/applications/{self.application.id}/acknowledgements/'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 401)

    def test_all_will_return_all_active_acknowledgements(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            url = f'/api/1.0.0/agent-user/applications/{self.application.id}/acknowledgements/all-active/'
            
            response = self.client.get(url, **self.headers, format='json')
            response_json = response.json()
    
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response_json), 2)
            self.assertEqual(response_json[0].get('disclosure').get('id'), str(self.document.id))
            self.assertEqual(response_json[0].get('disclosure').get('name'), self.document.name)
            self.assertEqual(response_json[0].get('is_acknowledged'), False)
            self.assertEqual(response_json[1].get('is_acknowledged'), True)
