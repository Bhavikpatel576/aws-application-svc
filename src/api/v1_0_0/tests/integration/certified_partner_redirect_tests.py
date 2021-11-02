from django.conf import settings
from rest_framework.test import APITestCase

from application.models.brokerage import Brokerage
from application.models.real_estate_agent import RealEstateAgent


class CertifiedPartnerRedirectTests(APITestCase):
    def test_redirect_works_with_dashy_phone(self):
        agent = RealEstateAgent.objects.create(name="Blake Outlaw", phone='512-555-1234', email='blake@homeward.com',
                                               company='Homeward', is_certified=True, sf_id='blah')

        url = '/agent/5125551234'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], f"{settings.ONBOARDING_BASE_URL}agent/{agent.id}")

    def test_redirect_works_with_dot_phone(self):
        agent = RealEstateAgent.objects.create(name="Blake Outlaw", phone='512.555.1234', email='blake@homeward.com',
                                               company='Homeward', is_certified=True, sf_id='blah')

        url = '/agent/5125551234'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], f"{settings.ONBOARDING_BASE_URL}agent/{agent.id}")

    def test_redirect_works_with_sf_phone(self):
        agent = RealEstateAgent.objects.create(name="Blake Outlaw", phone='(512) 555-1234', email='blake@homeward.com',
                                               company='Homeward', is_certified=True, sf_id='blah')

        url = '/agent/5125551234'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], f"{settings.ONBOARDING_BASE_URL}agent/{agent.id}")

    def test_redirect_works_with_flat_phone(self):
        agent = RealEstateAgent.objects.create(name="Blake Outlaw", phone='5121112222',
                                               email='blake@homeward.com',
                                               company='Homeward', is_certified=True, sf_id='blah')

        url = '/agent/5121112222'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], f"{settings.ONBOARDING_BASE_URL}agent/{agent.id}")

    def test_redirects_to_normal_app_if_not_found(self):
        url = '/agent/9999999999'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], settings.ONBOARDING_BASE_URL)

    def test_exception_with_too_long_phone_number(self):
        url = '/agent/999999999999999'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], settings.ONBOARDING_BASE_URL)

    def test_redirect_works_with_dashy_country_code(self):
        agent = RealEstateAgent.objects.create(name="Blake Outlaw", phone='1-512-555-1234', email='blake@homeward.com',
                                               company='Homeward', is_certified=True, sf_id='blah')

        url = '/agent/5125551234'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], f"{settings.ONBOARDING_BASE_URL}agent/{agent.id}")

    def test_redirect_works_with_flat_country_code(self):
        agent = RealEstateAgent.objects.create(name="Blake Outlaw", phone='15125551234', email='blake@homeward.com',
                                               company='Homeward', is_certified=True, sf_id='blah')

        url = '/agent/5125551234'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], f"{settings.ONBOARDING_BASE_URL}agent/{agent.id}")

    def test_redirect_works_for_non_certified_broker_partner_agent(self):
        brokerage = Brokerage.objects.create(name='Realty Austin')
        agent = RealEstateAgent.objects.create(name="Blake Outlaw", phone='15125551234', email='blake@homeward.com',
                                               company='Homeward', is_certified=False, brokerage=brokerage)
        url = '/agent/5125551234'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], f"{settings.ONBOARDING_BASE_URL}agent/{agent.id}")

    def test_redirect_to_normal_site_for_non_partner_non_certified_agent(self):
        brokerage = Brokerage.objects.create(name='Not Realty Austin')
        RealEstateAgent.objects.create(name="Blake Outlaw", phone='15125551234', email='blake@homeward.com',
                                               company='Homeward', is_certified=False, brokerage=brokerage)
        url = '/agent/5125551234'

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response._headers.get('location')[1], settings.ONBOARDING_BASE_URL)
