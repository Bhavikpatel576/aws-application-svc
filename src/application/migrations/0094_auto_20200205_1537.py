# Generated by Django 2.2 on 2020-02-05 15:37

from django.db import migrations
from django.db.migrations import RunPython


def add_dependency_to_mortgage_task(apps, schema_editor):
    return
    # turns out this was wrong, whoops!
    # TaskDependency = apps.get_model("application", "TaskDependency")
    # Task = apps.get_model("application", "Task")
    #
    # mortgage_task = Task.objects.get(category=TaskCategory.MORTGAGE_PREAPPROVAL)
    # disclosure_task = Task.objects.get(category=TaskCategory.DISCLOSURES)
    # TaskDependency.objects.create(parent_task=mortgage_task, depends_on=disclosure_task)


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0093_taskdependency'),
    ]

    operations = [
        migrations.RunPython(add_dependency_to_mortgage_task, RunPython.noop),
    ]