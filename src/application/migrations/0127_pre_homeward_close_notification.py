# Generated by Django 2.2 on 2020-06-10 20:03

from django.db import migrations
from django.db.migrations import RunPython


def add_notification(apps, schema_editor):
    Notification = apps.get_model("application", "Notification")
    Notification.objects.create(name='pre-homeward close', type='email')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0126_pre_customer_close_notification'),
    ]

    operations = [
        migrations.RunPython(add_notification, RunPython.noop),
    ]
