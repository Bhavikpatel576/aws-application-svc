from datetime import datetime, timedelta
import pytz

from rest_framework.test import APITestCase
from application import constants
from api.v1_0_0.tests.integration.mixins import AuthMixin
from application.models.acknowledgement import Acknowledgement
from application.models.application import Application
from application.models.customer import Customer
from application.models.disclosure import Disclosure
from application.models.task_name import TaskName
from application.models.task_progress import TaskProgress
from application.models.task_status import TaskStatus
from application.task_operations import run_task_operations


class AcknowledgementTests(AuthMixin, APITestCase):
    def test_get_acknowledgements(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        other_application = self.create_application("other")

        # create two relevant to the test application, and one for a different app, to make sure we dont leak data
        Acknowledgement.objects.create(application=application, disclosure=document)
        Acknowledgement.objects.create(application=application, disclosure=document)
        Acknowledgement.objects.create(application=other_application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/'

        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        response = self.client.get(url, **headers, format='json')
        response_json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response_json), 2)

        self.assertEqual(response_json[0].get('disclosure').get('id'), str(document.id))
        self.assertEqual(response_json[0].get('disclosure').get('name'), document.name)
        self.assertEqual(response_json[0].get('disclosure').get('document_url'), document.document_url)
        self.assertEqual(response_json[0].get('is_acknowledged'), False)
        self.assertEqual(response_json[0].get('updated_at'), response_json[0]['updated_at'])

    def test_get_acknowledgements_with_invalid_token(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/'

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format('blah')
        }

        response = self.client.get(url, **headers, format='json')

        self.assertEqual(response.status_code, 401)

    def test_get_acknowledgements_with_no_token(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 401)

    def test_update_acknowledgements(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/{}/'.format(acknowledgement.id)

        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        acknowledgement = {
            'is_acknowledged': True,
        }

        response = self.client.patch(url, acknowledgement, **headers, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('ip_address'), '127.0.0.1')
        self.assertEqual(response.json().get('is_acknowledged'), True)
        acknowledged_at = datetime.strptime(response.json().get('acknowledged_at').split('.')[0], "%Y-%m-%dT%H:%M:%S")
        now = datetime.now()
        self.assertTrue(abs(now - acknowledged_at) < timedelta(seconds=2))

    def test_update_acknowledgements_with_invalid_token(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/{}/'.format(acknowledgement.id)

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format('blah')
        }

        acknowledgement = {
            'is_acknowledged': True
        }

        response = self.client.patch(url, acknowledgement, **headers, format='json')

        self.assertEqual(response.status_code, 401)

    def test_update_acknowledgements_with_no_token(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/{}/'.format(acknowledgement.id)

        acknowledgement = {
            'is_acknowledged': True
        }

        response = self.client.patch(url, acknowledgement, format='json')

        self.assertEqual(response.status_code, 401)

    def test_cant_update_someone_elses_acknowledgements(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        customer = Customer.objects.create(name='Test User', email='brandon@homeward.com')
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/{}/'.format(acknowledgement.id)

        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        acknowledgement = {
            'is_acknowledged': True,
        }

        response = self.client.patch(url, acknowledgement, **headers, format='json')

        self.assertEqual(response.status_code, 404)

    def test_update_acknowledgement_updates_task_progress(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=document)

        run_task_operations(application)

        disclosure_status = TaskStatus.objects.get(application=application, task_obj__name=TaskName.DISCLOSURES)

        self.assertEqual(disclosure_status.status, TaskProgress.NOT_STARTED)

        url = '/api/1.0.0/acknowledgement/{}/'.format(acknowledgement.id)

        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        acknowledgement = {
            'is_acknowledged': True,
        }

        response = self.client.patch(url, acknowledgement, **headers, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('ip_address'), '127.0.0.1')

        disclosure_status = TaskStatus.objects.get(application=application, task_obj__name=TaskName.DISCLOSURES)
        self.assertEqual(disclosure_status.status, TaskProgress.COMPLETED)

    def test_update_acknowledgement_does_not_update_task_progress_of_inactive_disclosure(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=False)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        Acknowledgement.objects.create(application=application, disclosure=document)

        run_task_operations(application)

        disclosure_statuses = TaskStatus.objects.filter(application=application, task_obj__name=TaskName.DISCLOSURES)

        self.assertFalse(disclosure_statuses.exists())

        document.active = True
        document.save()

        run_task_operations(application)

        disclosure_statuses = TaskStatus.objects.filter(application=application, task_obj__name=TaskName.DISCLOSURES)

        self.assertTrue(disclosure_statuses.exists())
        self.assertEqual(disclosure_statuses[0].status, TaskProgress.NOT_STARTED)

    def test_will_not_update_acknowledgement_at_if_value_present(self):
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/{}/'.format(acknowledgement.id)

        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        data = {
            'is_acknowledged': True,
        }

        response = self.client.patch(url, data, **headers, format='json')
        acknowledgement.refresh_from_db()
        acknowledged_at_time = acknowledgement.acknowledged_at

        self.assertEqual(response.status_code, 200)

        disclosure = Disclosure.objects.create(name="new disclosure", document_url="www.test.com")
        updated_data = {
            'disclosure_id': disclosure.id
        }

        response = self.client.patch(url, updated_data, **headers, format='json')

        self.assertEqual(response.json().get('acknowledged_at').split('.')[0], acknowledged_at_time.strftime("%Y-%m-%dT%H:%M:%S"))
    
    def test_should_not_allow_acknowledged_at_to_be_updated(self): 
        document = Disclosure.objects.create(name="test doc", document_url="http://www.google.com", active=True)
        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=document)

        url = '/api/1.0.0/acknowledgement/{}/'.format(acknowledgement.id)

        token = self.create_and_login_user('fakeloginuser')

        headers = {
            'HTTP_AUTHORIZATION': 'Token {}'.format(token)
        }

        data = {
            'is_acknowledged': True,
        }

        response = self.client.patch(url, data, **headers, format='json')
        acknowledgement.refresh_from_db()
        acknowledged_at_time = acknowledgement.acknowledged_at

        self.assertEqual(response.status_code, 200)
        updated_data = {
            'acknowledged_at': datetime.now()
        }

        response = self.client.patch(url, updated_data, **headers, format='json')

        self.assertEqual(response.json().get('acknowledged_at').split('.')[0], acknowledged_at_time.strftime("%Y-%m-%dT%H:%M:%S"))
    
    def test_multiple_service_agreements_returns_latest_date(self):
        disclosure_one = Disclosure.objects.create(name=constants.SERVICE_AGREEMENT_TX, document_url="http://www.google.com", active=True)
        disclosure_two = Disclosure.objects.create(name=constants.SERVICE_AGREEMENT_TX_RA, document_url="http://www.google.com", active=True)

        user_email = 'test_fakeloginuser@fakeloginusermail.com'
        customer = Customer.objects.create(name='Test User', email=user_email)
        application = Application.objects.create(customer=customer, listing_agent=None, buying_agent=None)
        acknowledgement = Acknowledgement.objects.create(application=application, disclosure=disclosure_one)

        acknowledgement.acknowledged_at = datetime.now(pytz.utc)
        acknowledgement.save()

        self.assertEqual(application.new_service_agreement_acknowledged_date, acknowledgement.acknowledged_at)

        new_acknowledgement_added = Acknowledgement.objects.create(application=application, disclosure=disclosure_two)
        new_acknowledgement_added.acknowledged_at = datetime.now(pytz.utc)
        new_acknowledgement_added.save()

        application.refresh_from_db()

        self.assertEqual(application.new_service_agreement_acknowledged_date, new_acknowledgement_added.acknowledged_at)