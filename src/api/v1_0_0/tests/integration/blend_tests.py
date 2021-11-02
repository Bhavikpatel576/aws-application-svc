from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status

from application.models.real_estate_agent import RealEstateAgent
from application.tests import random_objects
from api.v1_0_0.tests._utils import data_generators
from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.customer import Customer
from application.models.application import Application
from application.tests.random_objects import fake


class CustomerFollowupViewTests(AuthMixin, APITestCase):

    def setUp(self):
        self.url = f"/api/1.0.0/application/active/blend-followups"

        user = self.create_user('fakeapplicant')
        self.token = self.login_user(user)[1]
        customer = Customer.objects.create(name=fake.name(), email=user.email, phone=fake.phone_number())
        application = Application.objects.create(customer=customer)
        loan = random_objects.random_loan(application=application,
                                          blend_application_id='336f6e2c-6461-4cea-ae31-b176e186904d',
                                          salesforce_id='1')
        followup1 = random_objects.random_followup(loan=loan, application=application,
                                                   blend_followup_id='556f6e2c-6461-4cea-ae31-b176e1869441',
                                                   blend_application_id=loan.blend_application_id,
                                                   status='REQUESTED', followup_type='TAX_RETURN', description='2019')
        followup1 = random_objects.random_followup(loan=loan, application=application,
                                                   blend_followup_id='776f6e2c-6461-4cea-ae31-b176e1869555',
                                                   blend_application_id=loan.blend_application_id,
                                                   status='PENDING_REVIEW', followup_type='W2', description='2019')

        application2 = random_objects.random_application()
        loan2 = random_objects.random_loan(application=application2,
                                           blend_application_id='006f6e2c-6461-4cea-ae31-b176e186999c',
                                           salesforce_id='2')
        self.followup3 = random_objects.random_followup(loan=loan2, application=application2,
                                                        blend_followup_id='888f6e2c-6461-4cea-ae31-b176e1869111',
                                                        blend_application_id=loan2.blend_application_id,
                                                        status='REQUESTED', followup_type='TAX_RETURN',
                                                        description='2019')

    def test_get_blend_followups_for_customer(self):
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)
        }
        response = self.client.get(self.url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_get_blend_followups_for_unauthorized_customer(self):
        headers = {}
        response = self.client.get(self.url, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_blend_followups_for_customer_with_no_applications(self):
        user2 = self.create_user('fakeapplicant2')
        token2 = self.login_user(user2)[1]
        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token2)
        }
        url = f"/api/1.0.0/application/active/blend-followups"
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)


class AgentFollowupViewTests(AuthMixin, APITestCase):

    def setUp(self):
        self.url = f"/api/1.0.0/agent-user/applications/blend-followups"

        # Main Agent data
        c_1 = Customer.objects.create(name='Test User', email="c1@blah.blah")
        c_2 = Customer.objects.create(name='Test User', email="c2@blah.blah")
        self.user = self.create_user("fake_agent_user1")
        self.token = self.login_user(self.user)[1]
        self.headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)
        }

        self.agent = RealEstateAgent.objects.create(
            **data_generators.get_fake_real_estate_agent("agent", email=self.user.email))
        self.application_1 = Application.objects.create(customer=c_1, **data_generators.get_fake_application("agent",
                                                                                                             buying_agent=self.agent))
        self.application_2 = Application.objects.create(customer=c_2, **data_generators.get_fake_application("agent",
                                                                                                             buying_agent=self.agent))
        self.loan_1 = random_objects.random_loan(application=self.application_1,
                                                 blend_application_id='336f6e2c-6461-4cea-ae31-b176e186904d',
                                                 salesforce_id='1')
        loan1_followup1 = random_objects.random_followup(loan=self.loan_1, application=self.application_1,
                                                         blend_followup_id='556f6e2c-6461-4cea-ae31-b176e1869441',
                                                         blend_application_id=self.loan_1.blend_application_id,
                                                         status='REQUESTED', followup_type='TAX_RETURN',
                                                         description='2019')
        loan1_followup2 = random_objects.random_followup(loan=self.loan_1, application=self.application_1,
                                                         blend_followup_id='776f6e2c-6461-4cea-ae31-b176e1869555',
                                                         blend_application_id=self.loan_1.blend_application_id,
                                                         status='PENDING_REVIEW', followup_type='W2',
                                                         description='2019')

        self.loan_2 = random_objects.random_loan(application=self.application_2,
                                                 blend_application_id='888f6e2c-6461-4cea-ae31-b176e1869888',
                                                 salesforce_id='2')
        loan2_followup1 = random_objects.random_followup(loan=self.loan_2, application=self.application_2,
                                                         blend_followup_id='111f6e2c-6461-4cea-ae31-b176e1869441',
                                                         blend_application_id=self.loan_2.blend_application_id,
                                                         status='REQUESTED', followup_type='TAX_RETURN',
                                                         description='2020')

        # Other Agent data
        c_3 = Customer.objects.create(name='Test User', email="c3@blah.blah")
        self.user_2 = self.create_user("fake_agent_user2")
        self.token_2 = self.login_user(self.user_2)[1]
        self.headers_2 = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(self.token_2)
        }

        self.agent_2 = RealEstateAgent.objects.create(
            **data_generators.get_fake_real_estate_agent("agent2", email=self.user_2.email))
        self.application_3 = Application.objects.create(customer=c_3, **data_generators.get_fake_application("agent2",
                                                                                                             buying_agent=self.agent_2))
        self.loan_3 = random_objects.random_loan(application=self.application_3,
                                                 blend_application_id='000f6e2c-6461-4cea-ae31-b176e1869000',
                                                 salesforce_id='3')
        loan3_followup1 = random_objects.random_followup(loan=self.loan_3, application=self.application_3,
                                                         blend_followup_id='006f6e2c-6461-4cea-ae31-b176e1869400',
                                                         blend_application_id=self.loan_3.blend_application_id,
                                                         status='REQUESTED', followup_type='TAX_RETURN',
                                                         description='2021')

    def test_get_blend_followups_for_agent(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()

            response = self.client.get(self.url, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()), 3)

    def test_get_blend_followups_for_unauthorized_agent(self):
        headers = {}
        response = self.client.get(self.url, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_blend_followups_returns_only_followups_associated_with_agent(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent_2.email = self.agent_2.email.upper()
            self.agent_2.save()

            response = self.client.get(self.url, **self.headers_2)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()), 1)
