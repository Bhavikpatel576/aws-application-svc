# Generated by Django 2.2 on 2020-01-16 22:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0072_auto_20200103_2018'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='self_reported_referral_source',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
