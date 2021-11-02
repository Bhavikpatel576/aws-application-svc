# Generated by Django 2.2 on 2019-12-05 22:44

from django.db import migrations
from django.db.migrations import RunPython

from application.models.task_category import TaskCategory
from application.models.task_progress import TaskProgress


def add_photo_upload_task(apps, schema_editor):
    Application = apps.get_model("application", "Application")
    TaskStatus = apps.get_model("application", "TaskStatus")

    for app in Application.objects.all():
        if app.current_home:
            if app.current_home.images.count() > 4:
                TaskStatus.objects.create(application=app, task=TaskCategory.PHOTO_UPLOAD, status=TaskProgress.COMPLETED)
            elif app.current_home.images.count() > 0:
                TaskStatus.objects.create(application=app, task=TaskCategory.PHOTO_UPLOAD, status=TaskProgress.IN_PROGRESS)
            else:
                TaskStatus.objects.create(application=app, task=TaskCategory.PHOTO_UPLOAD, status=TaskProgress.NOT_STARTED)
        else:
            TaskStatus.objects.create(application=app, task=TaskCategory.PHOTO_UPLOAD, status=TaskProgress.COMPLETED)


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0066_realestatelead'),
    ]

    operations = [
        migrations.RunPython(add_photo_upload_task, RunPython.noop, elidable=True)
    ]
