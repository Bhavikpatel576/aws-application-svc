# Generated by Django 2.2 on 2020-01-23 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0078_auto_20200123_1937'),
    ]

    operations = [
        migrations.AddField(
            model_name='builder',
            name='self_reported_referral_source',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='builder',
            name='self_reported_referral_source_detail',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
