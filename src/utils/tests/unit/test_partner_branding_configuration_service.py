import os
from rest_framework.test import APITestCase
from unittest.mock import patch
from utils.partner_branding_config_service import get_partner
from requests import Session

class PartnerBrandingConfigServiceTests(APITestCase):
    module_dir = os.path.dirname(__file__)
    cms_config_payload = open(os.path.join(module_dir, '../static/cms_config.json')).read()


    @patch.object(Session, 'get')
    def test_should_get_partner_out_of_response(self, mock_get):
        slug = "vpp"
        mock_get.return_value.content = self.cms_config_payload
        mock_get.return_value.status_code = 200
        partner = get_partner(slug)
        self.assertEqual(partner['name'], 'Van Poole Properties Group')
