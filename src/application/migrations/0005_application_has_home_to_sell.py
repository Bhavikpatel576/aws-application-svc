# Generated by Django 2.2 on 2019-05-09 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0004_auto_20190509_0702'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='has_home_to_sell',
            field=models.BooleanField(default=False),
        ),
    ]
