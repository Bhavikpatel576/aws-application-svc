# Generated by Django 2.2 on 2020-02-19 18:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0108_auto_20200218_2308'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='internal_referral_detail',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
