import logging
from utils.homeward_oauth import HomewardOauthClient
import uuid

from django.conf import settings


logger = logging.getLogger(__name__)


class AgentServiceClientException(Exception):
    pass


class AgentServiceClient(HomewardOauthClient):
    def __init__(self):
        super().__init__()
        self.agent_service_base_endpoint = settings.AGENT_SERVICE_BASE_ENDPOINT

    def create_agent(self, data):
        response = self.client.post(f"{self.agent_service_base_endpoint}agents/", data=data)
        if response.status_code != 201:
            logger.error("Failed to create new agent", extra=dict(
                type="agent_svc_request_failed_during_create_agent",
                response=response.json(),
                status_code=response.status_code,
                reason=response.reason,
            ))
        return response

    def update_agent(self, agent_id, data):
        url = f"{self.agent_service_base_endpoint}agents/{agent_id}/"
        response = self.client.patch(url, data=data)
        if response.status_code != 200:
            logger.error("Failed to update agent", extra=dict(
                type="agent_svc_request_failed_during_update_agent",
                response=response.json(),
                status_code=response.status_code,
                reason=response.reason,
                agent_service_id=agent_id
            ))
        return response

    def get_agent_id(self, agent_service_verified_sso_id: uuid) -> dict:
        response = self.client.get(f'{self.agent_service_base_endpoint}agent/?sso_id={agent_service_verified_sso_id}')
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Failed to find agent id", extra=dict(
                type="agent_svc_bad_request_during_get_agent_id",
                response=response.json(),
                status_code=response.status_code,
                reason=response.reason,
                agent_service_verified_sso_id=agent_service_verified_sso_id
            ))
            return None
