import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponseRedirect
from rest_framework import viewsets, permissions

from application.models.real_estate_agent import RealEstateAgent

logger = logging.getLogger(__name__)


class CertifiedPartnerRedirectViewSet(viewsets.ViewSet):
    permission_classes = (permissions.AllowAny, )

    def retrieve(self, request, phone):
        try:
            agent = RealEstateAgent.objects.get(Q(phone=phone) & Q(is_certified=True))
        except ObjectDoesNotExist:
            agent = RealEstateAgent.objects.filter(Q(phone=phone) & Q(brokerage__name='Realty Austin')).first()
            if agent is None:
                logger.warning(f"failed finding agent for phone number {phone}, redirecting to base url",
                               extra=dict(type='agent_phone_not_found'))
                return HttpResponseRedirect(settings.ONBOARDING_BASE_URL)
        except AssertionError:
            logger.warning(f"phone number provided was too long - {phone}",
                           extra=dict(type='certified_agent_phone_number_too_long'))
            return HttpResponseRedirect(settings.ONBOARDING_BASE_URL)

        redirect_url = settings.ONBOARDING_BASE_URL + "agent/" + str(agent.id)
        return HttpResponseRedirect(redirect_url)
