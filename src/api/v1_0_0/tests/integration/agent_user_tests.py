import uuid
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from api.v1_0_0.tests._utils import data_generators
from application.models.application import Application
from application.models.customer import Customer
from application.models.pricing import Pricing
from application.models.real_estate_agent import RealEstateAgent
from application.tests import random_objects

from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.tests.random_objects import fake


class AgentApplicationsViewTests(AuthMixin, APITestCase):

    def setUp(self):
        c = Customer.objects.create(name='Test User', email="blahblahblah@blah.blah")
        self.url = "/api/1.0.0/agent-user/applications/active/"
        self.new_url = "/api/1.0.0/agent-user/applications/"
        self.user = self.create_user("fake_agent_user1")
        self.token = self.login_user(self.user)[1]
        self.headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)
        }

        self.agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=self.user.email))
        self.application_1 = Application.objects.create(customer=c, **data_generators.get_fake_application("agent", buying_agent=self.agent))
        self.application_2 = Application.objects.create(customer=c, **data_generators.get_fake_application("agent", buying_agent=self.agent))
        self.offer_1 = random_objects.random_offer(application=self.application_1)
        self.offer_2 = random_objects.random_offer(application=self.application_2)
        self.loan = random_objects.random_loan(application=self.application_1,
                                               blend_application_id='000f6e2c-6461-4cea-ae31-b176e1869000',
                                               salesforce_id='3')

        self.other_agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("other_agent"))
        self.other_application = Application.objects.create(customer=c, **data_generators.get_fake_application("other_agent", buying_agent=self.other_agent))
        
        self.archive_url = "/api/1.0.0/agent-user/applications/application_id/archive/"
        self.unarchive_url = "/api/1.0.0/agent-user/applications/application_id/unarchive/"

    def test_get_active_applications(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()

            response = self.client.get(self.url, **self.headers)
            self.assertEqual(len(response.json()), 2)

            # It should only return applications for the logged-in user
            for a in response.json():
                self.assertIn(a['id'], [str(self.application_1.id), str(self.application_2.id)])
                self.assertIn(a['offers'][0]['id'], [str(self.offer_1.id), str(self.offer_2.id)])
                self.assertNotIn(a['id'], [str(self.other_application.id)])

            m.assert_called_once()

    def test_get_active_applications_no_perms(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedNoGroupsUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_get_active_applications_agent_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentOnlyUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_get_active_applications_email_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedVerifiedEmailUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_bad_request_fails_gracefully(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedBadRequestResponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()
    
    def test_get_all_applications(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()

            customer = Customer.objects.create(name='Test User', email="testuseremail@hello.com")
            archived_application_1 = Application.objects.create(customer=customer, **data_generators.get_fake_application("agent", buying_agent=self.agent), filter_status=['Archived'])
            archived_application_2 = Application.objects.create(customer=customer, **data_generators.get_fake_application("agent", buying_agent=self.agent), filter_status=['Archived'])

            response = self.client.get(self.new_url, **self.headers)

            json_response = response.json()
            self.assertEqual(len(json_response['archived']), 2)
            self.assertEqual(len(json_response['active']), 2)

    def test_get_all_applications_no_perms(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedNoGroupsUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_get_all_applications_agent_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentOnlyUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_get_all_applications_email_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedVerifiedEmailUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_bad_request_to_get_all_applications_fails_gracefully(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedBadRequestResponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_get_application_detail_with_offer(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.save()
            offer = random_objects.random_offer(application=application)

            url = '/api/1.0.0/agent-user/applications/{}/detail/'.format(application.id)

            response = self.client.get(url, **self.headers)
            json_response = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json_response['id'], str(application.id))
            self.assertEqual(json_response['offers'][0]['id'], str(offer.id))
            self.assertEqual(json_response['customer']['name'], application.customer.name)

    def test_get_application_detail_without_offer(self):
         with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.save()

            url = f"/api/1.0.0/agent-user/applications/{application.id}/detail/"

            response = self.client.get(url, **self.headers)
            json_response = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json_response['id'], str(application.id))
            self.assertEqual(json_response['customer']['name'], application.customer.name)
            self.assertEqual(json_response.get('offer'), None)

    def test_will_not_return_application_if_agent_is_not_buying_agent(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            user = self.create_user("fake_agent_user2")
            token = self.login_user(user)[1]
            headers = {
                'HTTP_AUTHORIZATION': 'Token {}'.format(token)
            }

            another_agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=user.email))
            url = f"/api/1.0.0/agent-user/applications/{self.application_1.id}/detail/"
            response = self.client.get(url, **headers)
            self.assertEqual(response.status_code, 404)

    def test_bad_request_fails_gracefully(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedBadRequestResponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            url = f"/api/1.0.0/agent-user/applications/{self.application_1.id}/detail/"

            response = self.client.get(url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_get_loan_for_application_with_and_without_loan(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()

            response = self.client.get(self.url, **self.headers)
            self.assertEqual(len(response.json()), 2)

            for a in response.json():
                if a['id'] == str(self.application_1.id):
                    self.assertIsNotNone(a['loan'])
                else:
                    self.assertEqual(a['loan'], {})

    def test_get_loan_for_application_with_multiple_loans(self):
        with patch("user.models.requests.get") as m:
            loan2 = random_objects.random_loan(application=self.application_1,
                                               blend_application_id='000f6e2c-6461-4cea-ae31-c176e1869000',
                                               salesforce_id='4')
            loan2.status = 'Withdrawn'
            loan2.save()
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()

            response = self.client.get(self.url, **self.headers)
            self.assertEqual(len(response.json()), 2)

            for a in response.json():
                if a['id'] == str(self.application_1.id):
                    self.assertIsNotNone(a['loan'])
                else:
                    self.assertEqual(a['loan'], {})
    
    def test_put_archived_application(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.save()
            
            response = self.client.put(self.archive_url.replace("application_id", str(application.id)), **self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn(str(application.id), response.data.get('message'))
            self.assertIn(Application.FilterStatus.ARCHIVED, Application.objects.get(id=application.id).filter_status)
            

    def test_put_archive_application_not_found(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.save()
            
            response = self.client.put(
                self.archive_url.replace("application_id", str(uuid.uuid4())),
                **self.headers)
            self.assertEqual(response.status_code, 404)
    
    def test_put_archive_application_already_archived(self): 
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.filter_status = ["Archived"]
            application.save()

            response = self.client.put(self.archive_url.replace("application_id", str(application.id)), **self.headers)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(f"Application {application.id} already archived", response.data.get('message'))
            self.assertIn(Application.FilterStatus.ARCHIVED, Application.objects.get(id=application.id).filter_status)
    
    def test_put_unarchive_application(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.filter_status = ["Archived"]
            application.save()
            
            response = self.client.put(self.unarchive_url.replace("application_id", str(application.id)), **self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn(str(application.id), response.data.get('message'))
            self.assertEqual([], Application.objects.get(id=application.id).filter_status)
    
    def test_put_unarchive_application_not_found(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.save()
            
            response = self.client.put(
                self.unarchive_url.replace("application_id", str(uuid.uuid4())),
                **self.headers)
            self.assertEqual(response.status_code, 404)
    
    def test_put_unarchive_application_already_no_archive_status(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            
            application = random_objects.random_application()
            application.buying_agent = self.agent
            application.save()
            
            response = self.client.put(self.unarchive_url.replace("application_id", str(application.id)), **self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(f"Application {application.id} is already not archived", response.data.get('message'))
            self.assertEqual([], Application.objects.get(id=application.id).filter_status)


class AgentQuotesViewTests(AuthMixin, APITestCase):

    @patch("application.models.pricing.homeward_salesforce")
    def setUp(self, salesforce_mock):
        salesforce_mock.create_new_salesforce_object.return_value = fake.pystr(max_chars=18)
        self.url = "/api/1.0.0/agent-user/quotes/active/"
        self.new_url = "/api/1.0.0/agent-user/quotes/"
        self.user = self.create_user("fake_agent_user1")
        self.token = self.login_user(self.user)[1]
        self.headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)
        }

        self.agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("agent", email=self.user.email))
        self.pricing_1 = Pricing.objects.create(agent=self.agent, **data_generators.get_fake_pricing())
        self.pricing_2 = Pricing.objects.create(agent=self.agent, **data_generators.get_fake_pricing())

        self.other_agent = RealEstateAgent.objects.create(**data_generators.get_fake_real_estate_agent("other_agent"))
        self.other_pricing = Pricing.objects.create(agent=self.other_agent, **data_generators.get_fake_pricing())

        self.archive_url = f"/api/1.0.0/agent-user/quotes/{self.pricing_1.id}/archive/"

    def test_get_active_quotes(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            response = self.client.get(self.url, **self.headers)
            self.assertEqual(len(response.json()), 2)
            for a in response.json():
                self.assertIn(a['id'], [str(self.pricing_1.id), str(self.pricing_2.id)])
                self.assertIsNotNone(a['updated_at'])
                self.assertIsNotNone(a['questionnaire_response_id'])
                self.assertNotIn(a['id'], [str(self.other_pricing.id)])
            m.assert_called_once()

    def test_get_active_quotes_no_perms(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedNoGroupsUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            # It should attempt to refresh the user's groups from CAS
            m.assert_called_once()

    def test_get_active_quotes_agent_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentOnlyUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            # It should attempt to refresh the user's groups from CAS
            m.assert_called_once()

    def test_get_active_quotes_email_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedVerifiedEmailUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            # It should attempt to refresh the user's groups from CAS
            m.assert_called_once()

    def test_bad_request_fails_gracefully(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedBadRequestResponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()
    
    def test_get_active_quotes(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()
            response = self.client.get(self.new_url, **self.headers)
            json_response = response.json()
            self.assertEqual(len(json_response['active']), 2)
            for a in json_response['active']:
                self.assertIn(a['id'], [str(self.pricing_1.id), str(self.pricing_2.id)])
                self.assertIsNotNone(a['updated_at'])
                self.assertIsNotNone(a['questionnaire_response_id'])
                self.assertNotIn(a['id'], [str(self.other_pricing.id)])
            m.assert_called_once()

    def test_get_active_quotes_does_not_include_archived_quotes(self): 
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentUserResponse()

            archived_pricing_1 = Pricing.objects.create(agent=self.agent, **data_generators.get_fake_pricing(), filter_status=['Archived'])

            response = self.client.get(self.new_url, **self.headers)
            json_response = response.json()
            self.assertEqual(len(json_response['active']), 2)
            for a in json_response['active']:
                self.assertIn(a['id'], [str(self.pricing_1.id), str(self.pricing_2.id)])
                self.assertIsNotNone(a['updated_at'])
                self.assertIsNotNone(a['questionnaire_response_id'])
                self.assertNotIn(a['id'], [str(self.other_pricing.id)])
            m.assert_called_once()

    def test_get_all_quotes_no_perms(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedNoGroupsUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            # It should attempt to refresh the user's groups from CAS
            m.assert_called_once()

    def test_get_all_quotes_agent_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedAgentOnlyUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            # It should attempt to refresh the user's groups from CAS
            m.assert_called_once()

    def test_get_all_quotes_email_only(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedVerifiedEmailUserReponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            # It should attempt to refresh the user's groups from CAS
            m.assert_called_once()

    def test_get_all_quotes_bad_request_fails_gracefully(self):
        with patch("user.models.requests.get") as m:
            m.return_value = data_generators.MockedBadRequestResponse()
            token = self.create_and_login_user('fakeloginuser')
            headers = {'HTTP_AUTHORIZATION': 'Token {}'.format(token)}
            response = self.client.get(self.new_url, **headers)

            # It should fail because the user doesn't have correct group memberships
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            m.assert_called_once()

    def test_put_archive_quote(self):
        with patch("user.models.requests.get") as m:
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            m.return_value = data_generators.MockedAgentUserResponse()
            response = self.client.put(self.archive_url, **self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn(str(self.pricing_1.id), response.data.get('message'))
            self.assertIn(Pricing.FilterStatus.ARCHIVED.name, Pricing.objects.get(id=self.pricing_1.id).filter_status)

    def test_put_archive_quote_not_found(self):
        with patch("user.models.requests.get") as m:
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            m.return_value = data_generators.MockedAgentUserResponse()
            response = self.client.put(
                self.archive_url.replace(str(self.pricing_1.id), str(uuid.uuid4())),
                **self.headers)
            self.assertEqual(response.status_code, 404)

    @patch("application.models.pricing.homeward_salesforce")
    def test_put_archive_quote_already_archived(self, sf_mock):
        with patch("user.models.requests.get") as m:
            sf_mock.create_new_salesforce_object.return_value = fake.pystr(max_chars=18)
            self.agent.email = self.agent.email.upper()
            self.agent.save()
            self.pricing_1.filter_status.append(Pricing.FilterStatus.ARCHIVED.name)
            self.pricing_1.save()
            m.return_value = data_generators.MockedAgentUserResponse()
            response = self.client.put(self.archive_url, **self.headers)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(f"Quote {self.pricing_1.id} already archived", response.data.get('message'))
            self.assertIn(Pricing.FilterStatus.ARCHIVED.name, Pricing.objects.get(id=self.pricing_1.id).filter_status)