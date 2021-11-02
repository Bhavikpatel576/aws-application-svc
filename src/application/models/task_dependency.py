from django.db import models

from application.models.task import Task
from utils.models import CustomBaseModelMixin


class TaskDependency(CustomBaseModelMixin):
    parent_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(Task, on_delete=models.CASCADE)
