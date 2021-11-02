from rest_framework import status
from rest_framework.exceptions import APIException


class AgentUserSetupAPIException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Server error occured in AgentUserSetup"
    default_code = "agent_user_setup_failed"

    def __init__(self, detail, status_code):
        if status_code is not None:
            self.status_code = status_code
        if detail is not None:
            self.detail = detail
