# Generated by Django 2.2 on 2021-05-03 20:36

from django.db import migrations
from django.db.migrations import RunPython


def add_e_consent_disclosure(apps, schema_editor):
    Disclosure = apps.get_model("application", "Disclosure")
    Disclosure.objects.create(name="homeward e-consent",
                              document_url='https://storage.googleapis.com/acknowledgeable_documents/Electronic-Consent-V1.pdf',
                              disclosure_type='e_consent',
                              active=False)
    return


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0217_merge_20210429_2116'),
    ]

    operations = [
        migrations.RunPython(add_e_consent_disclosure, RunPython.noop),
    ]