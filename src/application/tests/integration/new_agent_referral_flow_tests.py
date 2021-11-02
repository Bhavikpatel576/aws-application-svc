import os
from pathlib import Path
from unittest.mock import patch

from rest_framework.test import APITestCase

from application.models.application import Application
from application.tasks import convert_response_to_application
from application.tests import random_objects


class NewAgentReferralFlowTests(APITestCase):
    module_dir = str(Path(__file__).parent)
    referral_flow_payload = open(os.path.join(module_dir, '../static/new_agent_referral_response.json')).read()

    @patch('application.tasks.push_to_salesforce')
    @patch('utils.mailer.send_agent_registration_notification')
    @patch('utils.mailer.send_agent_referral_welcome_email')
    def test_new_agent_referral_flow_payload(self, client_email_patch, agent_email_patch, sf_patch):
        random_objects.random_pricing(id='6ad32f10-8de8-4f39-9b60-a74dbd017fce')
        convert_response_to_application(self.referral_flow_payload)

        application = Application.objects.first()

        agent_email_patch.assert_called_once()
        client_email_patch.assert_called_with(application.customer, application.buying_agent, application.get_pricing_url())
