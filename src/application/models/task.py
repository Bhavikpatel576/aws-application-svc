import datetime

from django.contrib.postgres.fields import JSONField
from django.db import models

from application.models.task_category import TaskCategory
from utils.models import CustomBaseModelMixin


class Task(CustomBaseModelMixin):
    name = models.CharField(max_length=50, unique=True)
    category = models.CharField(choices=[(tag.value, tag.value) for tag in TaskCategory], max_length=50)
    order = models.IntegerField(default=100)
    start_date = models.DateField(auto_now_add=True, blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=False)
    state = models.CharField(max_length=50, blank=True, null=True)
    partner = models.CharField(max_length=50, blank=True, null=True)
    options = JSONField(blank=True, null=True, default=dict)
    is_editable = models.BooleanField(default=False)

    def is_active(self) -> bool:
        if self.start_date and self.end_date:
            now = datetime.date.today()
            return self.active and self.start_date < now < self.end_date
        else:
            return self.active
