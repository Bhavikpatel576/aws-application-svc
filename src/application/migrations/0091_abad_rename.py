# Generated by Django 2.2 on 2020-02-04 21:54
from django.db.migrations import RunPython

from django.db import migrations
from application.models.task_category import TaskCategory
from application.models.task_name import TaskName

def rename_abad_task(apps, schema_editor):
    Task = apps.get_model("application", "Task")
    Task.objects.filter(name="abad").update(name=TaskName.DISCLOSURES, category=TaskCategory.DISCLOSURES, order=4)

class Migration(migrations.Migration):

    dependencies = [
        ('application', '0090_auto_20200204_2137'),
    ]

    operations = [
        migrations.RunPython(rename_abad_task, RunPython.noop),
    ]
