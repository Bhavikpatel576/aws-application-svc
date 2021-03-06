# Generated by Django 2.2 on 2020-11-05 02:00
from django.db import migrations
from django.db.migrations import RunPython


def add_fast_track_notification(apps, schema_editor):
    Notification = apps.get_model("application", "Notification")
    Notification.objects.create(name='fast track resume', type='email')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0172_auto_20201026_1848'),
    ]

    operations = [
        migrations.RunPython(add_fast_track_notification, RunPython.noop),
    ]