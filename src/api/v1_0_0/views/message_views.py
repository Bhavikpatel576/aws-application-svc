import logging
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.v1_0_0.serializers.message_serializer import MessageSerializer

from utils.salesforce import homeward_salesforce
from utils import mailer

from application.models.models import Application

logger = logging.getLogger(__name__)

class MessageViewSet(viewsets.ViewSet):
    http_method_names = ['post']
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            try:
                resp = self.send_cx_manager_message(serializer.validated_data.get('body'), self.request.user.email)
                if resp.status_code != 200:
                    return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    return Response(status=status.HTTP_200_OK)
            except NoCXException as e:
                return Response(e.message, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            except MessageViewException as e:
                logger.exception("Failed to send cx manager message", exc_info=e,
                                 extra=dict(type="failed_to_send_cx_message"))
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_cx_manager_message(self, message_to_send: str, application_email: str):
        try:
            application = Application.objects.get(customer__email=application_email)
        except Application.DoesNotExist as err:
            raise MessageViewException("Unable to send cx_message, no application exists for {}".format(application_email)) from err

        if not application.cx_manager:
            raise NoCXException("Unable to send cx message, no cx exists on application for {}".format(application_email))

        if not application.new_salesforce:
            logger.error("Missing salesforce ID on application", extra=dict(
                type="missing_salesforce_id_on_application_for_send_cx_manager",
                application_id=application.id,
                application_email=application_email,
                message_to_send=message_to_send
            ))
            sf_url = None
        else:
            sf_url = homeward_salesforce.build_sf_url(application.new_salesforce)
        return mailer.send_cx_manager_message(application.cx_manager.email, message_to_send, application.customer.name, application.customer.email, sf_url)


class MessageViewException(Exception):
    pass

class NoCXException(Exception):
    def __init__(self, message):
        self.message = message
