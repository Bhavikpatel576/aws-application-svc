# Generated by Django 2.2 on 2020-06-22 14:11

from django.db import migrations
from django.db.migrations import RunPython


def add_notification(apps, schema_editor):
    Notification = apps.get_model("application", "Notification")
    Notification.objects.create(name='agent cma request', type='email')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0134_auto_20200612_2049'),
    ]

    operations = [
        migrations.RunPython(add_notification, RunPython.noop),
    ]
