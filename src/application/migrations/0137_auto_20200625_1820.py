# Generated by Django 2.2 on 2020-06-25 18:20

from django.db import migrations
from django.db.migrations import RunPython


def add_notification(apps, schema_editor):
    Notification = apps.get_model("application", "Notification")
    Notification.objects.create(name='agent pre-customer close', type='email')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0136_notification_template_id'),
    ]

    operations = [
        migrations.RunPython(add_notification, RunPython.noop),
    ]
