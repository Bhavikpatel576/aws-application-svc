"""
API v1 URL routers.
"""

from django.urls import path, re_path
from rest_framework.routers import SimpleRouter

from api.v1_0_0.views import (AcknowledgementViewSet,
                              ApplicationCurrentHomeViewSet,
                              ApplicationCurrentHomeImageViewSet,
                              ApplicationViewSet, BrokerageViewSet,
                              CurrentHomeImageViewSet,
                              LeadViewSet, MarketValuationViewSet,
                              MessageViewSet, MortgageLenderViewSet,
                              RealEstateAgentViewSet)
from api.v1_0_0.views.agent_user_views import (AgentUserApplicationViewSet,
                                               AgentUserQuoteViewSet)
from api.v1_0_0.views.application_views import NoteViewSet
from api.v1_0_0.views.blend_views import (AgentFollowupView,
                                          CustomerFollowupView)
from api.v1_0_0.views.market_value_analysis_views import (
    ComparableViewSet, MarketValueOpinionCommentViewSet)
from api.v1_0_0.views.new_home_purchase_views import NewHomePurchaseViewSet
from api.v1_0_0.views.offer_views import OfferViewSet
from api.v1_0_0.views.pricing_views import PricingViewSet
from api.v1_0_0.views.proxy_views import (CreateAgentViewSet,
                                          add_user_to_cas_groups,
                                          proxy_resend_verify_email)
from api.v1_0_0.views.real_estate_agent_views import CertifiedAgentViewSet
from api.v1_0_0.views.transaction_views import TransactionView
from api.v1_0_0.views.user_application_views import UserApplicationViewSet
from api.v1_0_0.views.user_views import (CASView, LogoutView, MEView,
                                         UserCustomViewViewSet)

ROUTER = SimpleRouter()

ROUTER.register(r'user/custom-view', UserCustomViewViewSet, basename="user-custom-view")
ROUTER.register(r'application', ApplicationViewSet, basename='application')
ROUTER.register(r'application/(?P<application_id>[a-zA-Z0-9-]+)/current-home-image',
                ApplicationCurrentHomeImageViewSet,
                basename='current-home-application')
ROUTER.register(r'user/application', UserApplicationViewSet, basename='user-application')
ROUTER.register(r'market-valuation', MarketValuationViewSet, basename="market-valuation")
ROUTER.register(r'market-value-opinion-comment', MarketValueOpinionCommentViewSet,
                basename="market-value-opinion-comment")
ROUTER.register(r'comparable', ComparableViewSet, basename="comparable")
ROUTER.register(r'notes', NoteViewSet)
ROUTER.register(r'lead', LeadViewSet, basename="lead")
ROUTER.register(r'acknowledgement', AcknowledgementViewSet, basename='acknowledgement')
ROUTER.register(r'agent', RealEstateAgentViewSet, basename='agent')
ROUTER.register(r'certified-agent', CertifiedAgentViewSet, basename='certified-agent')
ROUTER.register(r'brokerage', BrokerageViewSet, basename='brokerage')
ROUTER.register(r'pricing', PricingViewSet, basename='pricing')
ROUTER.register(r'message', MessageViewSet, basename='message')
ROUTER.register(r'proxy/agents', CreateAgentViewSet, basename='create-agent-view')
ROUTER.register(r'agent-user', AgentUserApplicationViewSet, basename='agent-user-applications')
ROUTER.register(r'agent-user', AgentUserQuoteViewSet, basename='agent-user-quotes')
ROUTER.register(r'offer', OfferViewSet, basename='offer')
ROUTER.register(r'mortgage-lender', MortgageLenderViewSet, basename='mortgage-lender')
ROUTER.register(r'new-home-purchase', NewHomePurchaseViewSet, basename='new-home-purchase')

__all__ = [
    'urlpatterns',
]

urlpatterns = [
    path('cas/auth', CASView.as_view(), name='cas-auth'),
    path('cas/logout', LogoutView.as_view(), name='cas-logout'),
    path('user/me', MEView.as_view(), name='user-me'),
    path('user/groups/add', add_user_to_cas_groups, name='user-add-groups'),
    path('current-home-image/', CurrentHomeImageViewSet.as_view(actions={'post': 'create'})),
    path('proxy/resend-verify-email/', proxy_resend_verify_email, name='resend-verify-email'),
    re_path(r'^current-home-image/(?P<key>[a-zA-Z0-9/.-]{1,})$',
            CurrentHomeImageViewSet.as_view(actions={'patch': 'update', 'delete': 'destroy'})),
    path('application/active/blend-followups', CustomerFollowupView.as_view(), name='customer-blend-followups'),
    path('agent-user/applications/blend-followups', AgentFollowupView.as_view(), name='agent-blend-followups'),
    path(r'application/<uuid:application_id>/current-home/', ApplicationCurrentHomeViewSet.as_view({'post': 'create', 'patch':'update'}),
         name='current-home-application'),
    path('transaction/salesforce/bulk/', TransactionView.as_view(), name='transaction')
] + ROUTER.urls
