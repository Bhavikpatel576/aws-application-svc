# Generated by Django 2.2 on 2021-02-22 18:52

from django.db import migrations
from django.db.migrations import RunPython


def add_notification(apps, schema_editor):
    Notification = apps.get_model("application", "Notification")
    Notification.objects.create(name='VPAL Incomplete', type='email')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0189_auto_20210211_1740'),
    ]

    operations = [
        migrations.RunPython(add_notification, RunPython.noop),
    ]
