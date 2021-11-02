# Generated by Django 2.2 on 2020-06-02 21:14

from django.db import migrations
from django.db.migrations import RunPython


def add_offer_submitted_notification(apps, schema_editor):
    Notification = apps.get_model("application", "Notification")
    Notification.objects.create(name='offer submitted', type='email')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0116_auto_20200602_2113'),
    ]

    operations = [
        migrations.RunPython(add_offer_submitted_notification, RunPython.noop),
    ]