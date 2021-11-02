from rest_framework import permissions
from application.models.offer import Offer
from application.models.application import Application
from application.models.real_estate_agent import RealEstateAgent
from user.constants import (
    HOMEWARD_SSO_CLAIMED_AGENT_GROUP,
    HOMEWARD_SSO_VERIFIED_EMAIL_GROUP
)


class IsAgentUser(permissions.BasePermission):
    def has_permission(self, request, view):
        user_groups = request.user.fetch_cas_groups()
        if HOMEWARD_SSO_CLAIMED_AGENT_GROUP in user_groups and HOMEWARD_SSO_VERIFIED_EMAIL_GROUP in user_groups:
            return True
        return False


class IsApplicationBuyingAgent(IsAgentUser):
    def has_permission(self, request, view):
        if super(IsApplicationBuyingAgent, self).has_permission(request, view):
            if request.method == 'POST':
                try:
                    application = Application.objects.get(id=request.data.get('application_id'))
                except Application.DoesNotExist:
                    try:
                        application = Application.objects.get(id=request.data.get('application'))
                    except Application.DoesNotExist:
                        application = None
                if application is None:
                    return False
                return self.verify_request_is_from_buying_agent(application, request.user)
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Offer):
            application = obj.application
            return self.verify_request_is_from_buying_agent(application, request.user)
        else:
            return self.verify_request_is_from_buying_agent(obj, request.user)

    def verify_request_is_from_buying_agent(self, object, user):
        buying_agent = getattr(object, "buying_agent", None)
        if isinstance(buying_agent, RealEstateAgent) and buying_agent.email.upper() == user.email.upper():
            return True
        return False


class IsPricingAgent(IsAgentUser):
    def has_object_permission(self, request, view, obj):
        agent = getattr(obj, "agent", None)
        if isinstance(agent, RealEstateAgent) and agent.email == request.user.email:
            return True
        return False
