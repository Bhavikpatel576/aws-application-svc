import logging
from utils.exceptions import AgentUserSetupAPIException
from api.v1_0_0.serializers.proxy_serializers import HomewardSSOAgentUserSerializer

import requests
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from utils.homeward_sso_client import HomewardSSO
from user.constants import (HOMEWARD_SSO_CLAIMED_AGENT_GROUP,
                            HOMEWARD_SSO_CUSTOMER_GROUP)

logger = logging.getLogger(__name__)


class CreateAgentViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.homeward_sso_util = HomewardSSO()

    def create(self, request):
        sso_agent_user_serializer = HomewardSSOAgentUserSerializer(data=request.data)
        sso_agent_user_serializer.is_valid(raise_exception=True)
        sso_create_resp = self.homeward_sso_util.create_agent_user(data=sso_agent_user_serializer.data)
        if sso_create_resp.status_code != status.HTTP_201_CREATED:
            raise AgentUserSetupAPIException(detail=f"Call to homeward sso failed with: {sso_create_resp.data}",
                                             status_code=sso_create_resp.status_code)
        else:
            return sso_create_resp




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_user_to_cas_groups(request):
    group_names = request.data.get("groups", [])
    bad_group_names = []
    for group_name in group_names:
        if group_name not in [HOMEWARD_SSO_CLAIMED_AGENT_GROUP, HOMEWARD_SSO_CUSTOMER_GROUP]:
            bad_group_names.append(group_name)
    if bad_group_names:
        return Response(f"The following group(s) are invalid: {bad_group_names}", status=status.HTTP_400_BAD_REQUEST)

    return HomewardSSO().update_user_groups(group_names, request.user.username)



@api_view(['POST'])
@permission_classes([AllowAny])
def proxy_resend_verify_email(request):
    email = request.data.get("email")
    payload = {"email": email}
    headers = {'Authorization': getattr(settings, 'HOMEWARD_SSO_AUTH_TOKEN')}
    url = getattr(settings, 'HOMEWARD_SSO_BASE_URL') + 'user/resend-verify-email'
    r = requests.post(url, json=payload, headers=headers)
    return Response(status=r.status_code)