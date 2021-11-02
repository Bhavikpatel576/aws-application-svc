"""
/agents/ test cases.
"""
import copy
from unittest.mock import patch

from parameterized import parameterized
from rest_framework.test import APITestCase

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.application import Application
from application.models.customer import Customer
from application.models.task_name import TaskName
from application.models.task_progress import TaskProgress
from application.task_operations import run_task_operations

valid_agent = {
    'name': 'new agent',
    'email': 'asdf@asdf.com',
    'phone': '111-222-3333',
    'company': 'asdf co.'
}

invalid_agent = {
    'name': 'new agent'
}


class AgentEndpointTests(AuthMixin, APITestCase):
    @parameterized.expand([
        ('happy path', 200, TaskProgress.COMPLETED, valid_agent, valid_agent, False, False, True, False),
        ('happy path needs listing', 200, TaskProgress.COMPLETED, None, valid_agent, True, False, True, False),
        ('happy path needs buying', 200, TaskProgress.COMPLETED, valid_agent, None, False, True, True, False),
        ('happy path needs listing & buying', 200, TaskProgress.COMPLETED, None, None, True, True, True, False),
        ('invalid listing agent', 400, None, invalid_agent, valid_agent, False, False, True, False),
        ('invalid buying agent', 400, None, valid_agent, invalid_agent, False, False, True, False),
        ('has listing agent, needs listing agent', 400, None, valid_agent, valid_agent, True, False, True, False),
        ('has buying agent, needs buying agent', 400, None, valid_agent, valid_agent, False, True, True, False),
        ('missing agent', 400, None, valid_agent, valid_agent, False, False, True, True),
        ('missing token', 401, None, valid_agent, valid_agent, False, False, False, False)
    ])
    @patch("application.tasks.push_agent_to_salesforce")
    def test_agents_endpoint(self, name, expected_response, expected_task_progress, listing_agent,
                             buying_agent, needs_listing_agent, needs_buying_agent, use_token, missing_agent,
                             mock_push_agent):
        url = '/api/1.0.0/application/agents/'
        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        if not use_token:
            headers = {}

        payload = {
            "listing_agent": listing_agent,
            "needs_listing_agent": needs_listing_agent,
            "buying_agent": buying_agent,
            "needs_buying_agent": needs_buying_agent
        }

        if missing_agent:
            del payload['listing_agent']

        user_email = 'test_fakeloginuser@fakeloginusermail.com'

        customer = Customer.objects.create(name='Test User', email=user_email)

        Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)

        resp = self.client.post(url, payload, **headers, format='json')

        self.assertEqual(resp.status_code, expected_response)

        updated_application = Application.objects.filter(customer__email=user_email).first()

        task = updated_application.task_statuses.filter(task_obj__name=TaskName.REAL_ESTATE_AGENT).first()
        if expected_task_progress is not None:
            self.assertEqual(task.status, expected_task_progress)
            if buying_agent is not None:
                self.assertEqual(updated_application.buying_agent.name, buying_agent['name'])
            if listing_agent is not None:
                self.assertEqual(updated_application.listing_agent.name, listing_agent['name'])
            self.assertEqual(updated_application.needs_listing_agent, needs_listing_agent)
            self.assertEqual(updated_application.needs_buying_agent, needs_buying_agent)

    @patch("application.tasks.push_agent_to_salesforce")
    def test_should_not_add_extra_agent_tasks(self, sf):
        url = '/api/1.0.0/application/agents/'
        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        payload = {
            "listing_agent": None,
            "needs_listing_agent": True,
            "buying_agent": valid_agent,
            "needs_buying_agent": False
        }

        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        agentTask = application.task_statuses.filter(task_obj__name=TaskName.REAL_ESTATE_AGENT)
        run_task_operations(application)

        self.assertEqual(agentTask.count(), 1)
        self.assertEqual(agentTask.first().status, TaskProgress.NOT_STARTED)

        run_task_operations(application)

        resp = self.client.post(url, payload, **headers, format='json')

        updated_application = Application.objects.filter(customer__email=user_email).first()
        task = updated_application.task_statuses.filter(task_obj__name=TaskName.REAL_ESTATE_AGENT)

        self.assertEqual(task.count(), 1)
        self.assertEqual(task.first().status, TaskProgress.COMPLETED)


    @patch("application.tasks.push_agent_to_salesforce")
    def test_optional_and_required_fields(self, mock_push_agent):
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)

        url = '/api/1.0.0/application/agents/'
        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        required_fields = ['name', 'email', 'phone']
        optional_fields = ['company']

        test_agent = {
            'name': 'new agent',
            'email': 'asdf@asdf.com',
            'phone': '111-222-3333',
            'company': 'asdf co.'
        }

        payload = {
            "listing_agent": test_agent,
            "needs_listing_agent": False,
            "buying_agent": test_agent,
            "needs_buying_agent": False
        }

        for field in required_fields:
            temp_payload = copy.deepcopy(payload)
            del temp_payload['listing_agent'][field]
            resp = self.client.post(url, temp_payload, **headers, format='json')
            self.assertEquals(resp.status_code, 400, "failed for field '{}'".format(field))

        for field in optional_fields:
            temp_payload = copy.deepcopy(payload)
            del temp_payload['listing_agent'][field]
            resp = self.client.post(url, temp_payload, **headers, format='json')
            self.assertEquals(resp.status_code, 200)
