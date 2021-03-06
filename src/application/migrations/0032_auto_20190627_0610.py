# Generated by Django 2.2 on 2019-06-27 06:10

from django.db import migrations
from utils import aws

def update_image_status(apps, schema_editor):
    current_home_image = apps.get_model('application', 'currenthomeimage')
    for image in current_home_image.objects.filter(status__in=['pending', 'uploaded']):
        if aws.check_if_object_exists(image.url):
            image.status = 'labeled'
            image.save()
        else:
            image.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('application', '0031_auto_20190626_0528'),
    ]

    operations = [
        migrations.RunPython(update_image_status, reverse_code=migrations.RunPython.noop, elidable=True)
    ]
