import os
from unittest.mock import patch

from parameterized import parameterized
from rest_framework.test import APITestCase

from utils import hubspot


class HubspotTests(APITestCase):
    module_dir = os.path.dirname(__file__)
    complete_hutk = 'de23751e33c7ec18a33a37a5df49051c'
    contact_payload = open(os.path.join(module_dir, '../static/hubspot_complete.json')).read()

    incomplete_hutk = '46f5b0be36ae6d90b5242941fca1a48c'
    not_contact_payload = open(os.path.join(module_dir, '../static/hubspot_not_contact.json')).read()

    @patch('utils.hubspot.requests.get')
    def test_should_get_lead_source(self, mock_get):
        mock_get.return_value.content = self.contact_payload
        lead_source_info = hubspot.get_lead_source_from_hubspot(self.complete_hutk)

        self.assertEqual(lead_source_info['lead_source'], 'PAID_SEARCH')
        self.assertEqual(lead_source_info['lead_source_drill_down_1'], 'Auto-tagged PPC')
        self.assertEqual(lead_source_info['lead_source_drill_down_2'], 'Unknown keywords (SSL)')

    @patch('utils.hubspot.requests.get')
    def test_should_raise_exception_when_not_contact(self, mock_get):
        mock_get.return_value.content = self.not_contact_payload

        with self.assertRaises(hubspot.HubspotContactNotFound):
            hubspot.get_lead_source_from_hubspot(self.complete_hutk)

    @patch('utils.hubspot.requests.post')
    def test_should_create_new_lead_source(self, mock_post):
        mock_post.return_value.status_code = 204
        it_worked = hubspot.create({})
        self.assertTrue(it_worked)

    @patch('utils.hubspot.requests.post')
    def test_should_return_false_with_wrong_response_code(self, mock_post):
        mock_post.return_value.status_code = 500
        it_worked = hubspot.create({})
        self.assertFalse(it_worked)

    @parameterized.expand([
        (204, True),
        (400, False),
        (401, False),
        (404, False),
        (500, False),
        (501, False),
    ])
    @patch('utils.hubspot.requests.post')
    def test_update_contact(self, status_code, expected, mock_post):
        mock_post.return_value.status_code = status_code
        it_worked = hubspot.update_contact('brandon@homeward.com', {})
        self.assertEqual(it_worked, expected)
