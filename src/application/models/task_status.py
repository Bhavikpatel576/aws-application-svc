from django.db import models

from application.models.application import Application
from application.models.task import Task
from application.models.task_progress import TaskProgress
from utils.models import CustomBaseModelMixin


class TaskStatus(CustomBaseModelMixin):
    """
    To store task status for application task status
    """
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="task_statuses")
    task_obj = models.ForeignKey(Task, on_delete=models.CASCADE, null=True)
    status = models.CharField(choices=[(tag.value, tag.value) for tag in TaskProgress],
                              default=TaskProgress.NOT_STARTED, max_length=50)

    def is_actionable(self) -> bool:
        dependencies = [dependency.depends_on for dependency in self.task_obj.dependencies.all()]
        if not dependencies:
            return True
        else:
            incomplete_dependent_tasks = self.application.task_statuses.filter(task_obj__in=dependencies)\
                .exclude(status=TaskProgress.COMPLETED).all()
            return 0 == len(incomplete_dependent_tasks)


    class Meta:
        ordering = ('created_at',)
        constraints = [
            models.UniqueConstraint(fields=['task_obj', 'application'], name='unique_taskstatus')
        ]
