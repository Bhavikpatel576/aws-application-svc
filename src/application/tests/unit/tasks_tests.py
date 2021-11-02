from uuid import uuid4
from django.test import TestCase
from parameterized import parameterized

from application.models.application import REAL_ESTATE_AGENT, REGISTERED_CLIENT, BUILDER, FAST_TRACK_REGISTRATION, \
    REFERRAL_LINK
from application.tasks import get_internal_referral_and_detail_from_referral_source, get_agent_id_from_agent_svc
from utils.agent_svc_client import AgentServiceClientException
from unittest import mock

class TasksTests(TestCase):
    @parameterized.expand([
        (REAL_ESTATE_AGENT, REAL_ESTATE_AGENT, REGISTERED_CLIENT),
        (BUILDER, BUILDER, REGISTERED_CLIENT),
        (FAST_TRACK_REGISTRATION, REAL_ESTATE_AGENT, FAST_TRACK_REGISTRATION),
        (REFERRAL_LINK, REAL_ESTATE_AGENT, REFERRAL_LINK),
        ("Apex Partner Site", "Apex Partner Site", 'Homeward', 'Homeward'),
        ("Apex Partner Site", "Apex Partner Site", None, None),
        ("SOMETHING ELSE", "SOMETHING ELSE", None)
    ])
    def test_getting_internal_referral(self, referral_source, expected_internal_referral,
                                       expected_internal_referral_detail, referral_source_detail=None):
        actual_internal_referral, actual_detail = \
            get_internal_referral_and_detail_from_referral_source(referral_source, referral_source_detail)

        self.assertEqual(expected_internal_referral, actual_internal_referral)
        self.assertEqual(expected_internal_referral_detail, actual_detail)

    """ return agent_svc_id if agent_service_verified_sso_id is provided """
    @mock.patch('application.tasks.AgentServiceClient')
    def test_get_agent_id_from_agent_svc(self, mock_agent_client):
        agent_svc_response = {'first_name': 'Andrea', 'id': '3617923766551'}
        mock_agent_client().get_agent_id.return_value = agent_svc_response
        self.assertEqual(get_agent_id_from_agent_svc('__test__'), agent_svc_response)

    """ throw error if we aren't able to recieve an agent_id given a valid agent_service_verified_sso_id """    
    @mock.patch('application.tasks.AgentServiceClient')
    def test_get_agent_id_from_agent_svc(self, mock_agent_client):
        mock_agent_client().get_agent_id.side_effect = AgentServiceClientException
        with self.assertRaises(AgentServiceClientException):
            get_agent_id_from_agent_svc('__test__')


    """ set agent_svc_id to Null if agent_service_verified_sso_id is not provided """
    @mock.patch('application.tasks.AgentServiceClient')
    def test_get_agent_id_from_agent_svc(self, mock_agent_client):
        agent_svc_response = None
        mock_agent_client().get_agent_id.return_value = agent_svc_response
        self.assertEqual(get_agent_id_from_agent_svc('__test__'), agent_svc_response)