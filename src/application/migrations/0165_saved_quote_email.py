# Generated by Django 2.2 on 2020-09-14 18:24

from django.db import migrations
from django.db.migrations import RunPython


def add_notification(apps, schema_editor):
    Notification = apps.get_model("application", "Notification")
    Notification.objects.create(name='saved quote', type='email')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0164_pricing_agent_situation'),
    ]

    operations = [
        migrations.RunPython(add_notification, RunPython.noop),
    ]