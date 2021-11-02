from django.db import models
from datetime import datetime

from application.models.disclosure import Disclosure
from application.models.application import Application
from utils.models import CustomBaseModelMixin
from utils.models import CustomBaseModelMixin, ModelDiffMixin


class Acknowledgement(CustomBaseModelMixin, ModelDiffMixin):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="acknowledgements")
    disclosure = models.ForeignKey(Disclosure, on_delete=models.CASCADE)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(default=None, blank=True, null=True)

    def save(self, *args, **kwargs):
        if 'is_acknowledged' in self.diff and self.acknowledged_at is None:
            self.acknowledged_at = datetime.now()

        super(Acknowledgement, self).save(*args, **kwargs)