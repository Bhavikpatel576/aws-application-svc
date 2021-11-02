from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from api.v1_0_0.tests._utils.data_generators import get_fake_real_estate_lead, get_fake_real_estate_lead_with_bad_payload
from application.models.real_estate_lead import RealEstateLead


class RealEstateLeadTestCase(APITestCase):
    def setUp(self):
        self.sf_patch = patch("application.tasks.push_to_salesforce")
        self.sf_patch.start()
        self.addCleanup(self.sf_patch.stop)
    def test_add_real_estate_lead(self):
        url = '/api/1.0.0/lead/'
        payload = get_fake_real_estate_lead()
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        lead: RealEstateLead = RealEstateLead.objects.get(customer__name='Bob Beaver')
        self.assertIsNotNone(lead)
        self.assertEqual(lead.home_buying_stage, 'researching online')
        self.assertEqual(lead.needs_buying_agent, True)
        self.assertEqual(lead.needs_listing_agent, False)

    def test_failing_to_add_real_estate_lead(self):
        url = '/api/1.0.0/lead/'
        payload = get_fake_real_estate_lead_with_bad_payload("phone")
        response = self.client.post(url, payload, format='json')
        response_json = response.json()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response_json)
        self.assertEqual(response_json['phone'], 'Phone must be set.')
