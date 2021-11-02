from django.db import models

from application.models.application import Application
from application.models.notification import Notification
from utils.models import CustomBaseModelMixin


class NotificationStatus(CustomBaseModelMixin):
    SENT = 'sent'
    SUPPRESSED = 'suppressed'
    NOT_SENT = 'not sent'

    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    reason = models.TextField(null=True, blank=True)
