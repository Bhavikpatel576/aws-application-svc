# Generated by Django 2.2 on 2021-02-03 18:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0186_pricing_salesforce_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='cxmanager',
            name='phone',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
