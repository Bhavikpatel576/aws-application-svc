from rest_framework import serializers

from user.constants import HOMEWARD_SSO_CLAIMED_AGENT_GROUP


class HomewardSSOAgentUserSerializer(serializers.Serializer):
    """
    Serializer for setting up an homeward agent sso user
    Claimed Agent is the default group for these types of users
    """
    email = serializers.CharField(default="")
    password = serializers.CharField(default="")
    first_name = serializers.CharField(default="")
    last_name = serializers.CharField(default="")
    group = serializers.CharField(default=HOMEWARD_SSO_CLAIMED_AGENT_GROUP)
    class Meta:
        fields = ["email", "password", "first_name", "last_name", "group"]
