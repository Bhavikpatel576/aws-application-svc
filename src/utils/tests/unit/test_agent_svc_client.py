import logging

from utils.agent_svc_client import AgentServiceClient
from unittest import mock
from uuid import uuid4
from django.test import SimpleTestCase
from utils import agent_svc_client

from utils import agent_svc_client, homeward_oauth


class MockResponse:
    def __init__(self, status_code, return_value=None, reason=None):
        self.status_code = status_code
        self.return_value = return_value
        self.reason = "" or reason

    def json(self):
        return self.return_value or {
            'agent': '__UUID__'
        }

class AgentServiceClientTests(SimpleTestCase):
    @mock.patch.object(homeward_oauth.OAuth2Session, 'fetch_token', return_value={'access_token': '_ASDF_'})
    @mock.patch('utils.homeward_oauth.OAuth2Session.get', return_value=MockResponse(200))
    def test_should_get_agent_id(self, mock_get_oauth, mock_fetch):
        self.assertEqual(agent_svc_client.AgentServiceClient().get_agent_id('__ID__'), {'agent': '__UUID__'})

    @mock.patch.object(homeward_oauth.OAuth2Session, 'fetch_token', return_value={'access_token': '_ASDF_'})
    @mock.patch('utils.homeward_oauth.OAuth2Session.get', return_value=MockResponse(400))
    def test_should_fail_to_get_agent_id(self, mock_get_oauth, mock_fetch):
        self.assertIsNone(agent_svc_client.AgentServiceClient().get_agent_id('__ID__'))

    @mock.patch.object(homeward_oauth.OAuth2Session, 'fetch_token', return_value={'access_token': '_ASDF_'})
    @mock.patch('utils.homeward_oauth.OAuth2Session.get', return_value=MockResponse(200))
    @mock.patch('utils.homeward_oauth.OAuth2Session.patch')
    def test_should_make_update_agent_call(self, mock_patch, mock_get_oauth, mock_fetch):
        agent_id = "4f315f0c-d08a-4c0a-acdd-d974b0eb841b"
        mock_patch.return_value = MockResponse(status_code=200)
        data = {"homeward_sso_user_id": 123456, "agent_id": agent_id}
        resp = AgentServiceClient().update_agent(agent_id, data)
        mock_patch.assert_called_with(f'https://agent-service-stage.herokuapp.com/agents/{agent_id}/', data=data)
        self.assertEqual(resp.status_code, 200)

    @mock.patch.object(homeward_oauth.OAuth2Session, 'fetch_token', return_value={'access_token': '_ASDF_'})
    @mock.patch('utils.homeward_oauth.OAuth2Session.get', return_value=MockResponse(200))
    @mock.patch('utils.homeward_oauth.OAuth2Session.post')
    def test_should_make_create_agent_call(self, mock_post, mock_get_oauth, mock_fetch):
        mock_post.return_value = MockResponse(status_code=201)
        data = {"homeward_sso_user_id": 123456}
        resp = AgentServiceClient().create_agent(data)
        mock_post.assert_called_with('https://agent-service-stage.herokuapp.com/agents/', data=data)
        self.assertEqual(resp.status_code, 201)

    @mock.patch.object(homeward_oauth.OAuth2Session, 'fetch_token', return_value={'access_token': '_ASDF_'})
    @mock.patch('utils.homeward_oauth.OAuth2Session.get', return_value=MockResponse(200))
    @mock.patch('utils.homeward_oauth.OAuth2Session.patch')
    def test_patch_should_return_resp_and_log_on_failure(self, mock_patch, mock_get_oauth, mock_fetch):
        agent_id = "4f315f0c-d08a-4c0a-acdd-d974b0eb841b"
        mock_patch.return_value = MockResponse(400, {"detail": "Bad Request!"})
        data = {"homeward_sso_user_id": 123456}
        logger = logging.getLogger('utils.agent_svc_client')
        with mock.patch.object(logger, 'error') as mock_error_log:
            resp = AgentServiceClient().update_agent(agent_id, data)
            mock_error_log.assert_called_once_with("Failed to update agent", extra=dict(
                type="agent_svc_request_failed_during_update_agent",
                response={"detail": "Bad Request!"},
                status_code=resp.status_code,
                reason=resp.reason,
                agent_service_id=agent_id
            ))
            mock_patch.assert_called_with(f'https://agent-service-stage.herokuapp.com/agents/{agent_id}/', data=data)
            self.assertEqual(resp.status_code, 400)

    @mock.patch.object(homeward_oauth.OAuth2Session, 'fetch_token', return_value={'access_token': '_ASDF_'})
    @mock.patch('utils.homeward_oauth.OAuth2Session.get', return_value=MockResponse(200))
    @mock.patch('utils.homeward_oauth.OAuth2Session.post')
    def test_post_should_return_resp_and_log_on_failure(self, mock_post, mock_get_oauth, mock_fetch):
        mock_post.return_value = MockResponse(400, {"detail": "Bad Request!"})
        data = {"homeward_sso_user_id": 123456}
        logger = logging.getLogger('utils.agent_svc_client')
        with mock.patch.object(logger, 'error') as mock_error_log:
            resp = AgentServiceClient().create_agent(data)
            mock_error_log.assert_called_once_with("Failed to create new agent", extra=dict(
                type="agent_svc_request_failed_during_create_agent",
                response={"detail": "Bad Request!"},
                status_code=resp.status_code,
                reason=resp.reason,
            ))
            mock_post.assert_called_with('https://agent-service-stage.herokuapp.com/agents/', data=data)
            self.assertEqual(resp.status_code, 400)