# Generated by Django 2.2 on 2019-09-03 23:02

from django.db import migrations
from django.db.migrations import RunPython


def convert_draft_to_incomplete(apps, schema_editor):
    Application = apps.get_model('application', 'Application')
    for application in Application.objects.filter(stage='draft'):
        application.stage = 'incomplete'
        application.save()


def convert_mortgage_approval_to_floor_price_valuation(apps, schema_editor):
    Application = apps.get_model('application', 'Application')
    for application in Application.objects.filter(stage='mortgage approval'):
        application.stage = 'floor price valuation'
        application.save()


def convert_max_offer_requested_to_offer_requested(apps, schema_editor):
    Application = apps.get_model('application', 'Application')
    for application in Application.objects.filter(stage='max offer requested'):
        application.stage = 'offer requested'
        application.save()


def convert_offer_negotiations_to_offer_submitted(apps, schema_editor):
    Application = apps.get_model('application', 'Application')
    for application in Application.objects.filter(stage='offer negotiations'):
        application.stage = 'offer submitted'
        application.save()


def convert_customer_purchase_to_customer_closed(apps, schema_editor):
    Application = apps.get_model('application', 'Application')
    for application in Application.objects.filter(stage='customer purchase'):
        application.stage = 'customer closed'
        application.save()


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0051_auto_20190903_2302'),
    ]

    operations = [
        migrations.RunPython(convert_draft_to_incomplete, RunPython.noop, elidable=True),
        migrations.RunPython(convert_mortgage_approval_to_floor_price_valuation, RunPython.noop, elidable=True),
        migrations.RunPython(convert_max_offer_requested_to_offer_requested, RunPython.noop, elidable=True),
        migrations.RunPython(convert_offer_negotiations_to_offer_submitted, RunPython.noop, elidable=True),
        migrations.RunPython(convert_customer_purchase_to_customer_closed, RunPython.noop, elidable=True),
    ]