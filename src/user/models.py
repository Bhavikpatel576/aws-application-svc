"""
User app models.
"""
import logging
import uuid
import requests

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.db import models
from utils.salesforce_model_mixin import (SalesforceModelMixin,
                                          SalesforceObjectType)

logger = logging.getLogger(__name__)


class User(AbstractUser, SalesforceModelMixin):
    # Salesforce Fields
    FIRST_APPLICATION_LOGIN_FIELD = "First_Application_Log_In__c"
    LAST_APPLICATION_LOGIN_FIELD = "Last_Application_Log_In__c"

    # Model Fields
    password = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        """
        Custom user object representation.
        """
        return "{} {}".format(self.first_name, self.last_name)

    def fetch_cas_groups(self):
        headers = {'Authorization': getattr(settings, 'HOMEWARD_SSO_AUTH_TOKEN')}
        user_endpoint = getattr(settings, 'HOMEWARD_SSO_BASE_URL') + 'user/{}/'.format(self.username)
        try:
            resp = requests.get(user_endpoint, headers=headers)
            resp.raise_for_status()
            cas_groups = resp.json().get("groups", [])
            return cas_groups
        except requests.RequestException as e:
            logger.exception("Unable to reach homeward-sso/user endpoint", exc_info=e, extra=dict(
                type="fetch_cas_groups_cant_reach_homewardsso",
                headers=headers,
                user_endpoint=user_endpoint,
            ))
        return []

    def salesforce_field_mapping(self):
        return {
            self.FIRST_APPLICATION_LOGIN_FIELD: self.date_joined.strftime("%Y-%m-%dT%H:%M:%S") if self.date_joined else None,
            self.LAST_APPLICATION_LOGIN_FIELD: self.last_login.strftime("%Y-%m-%dT%H:%M:%S") if self.last_login else None
        }

    def salesforce_object_type(self):
        return SalesforceObjectType.ACCOUNT


class UserCustomView(models.Model):
    """
    Model to store custom view of user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_view')
    is_shareable = models.BooleanField(default=False)
    application_listing_fields = JSONField()
    is_default = models.BooleanField(default=False)
