# Generated by Django 2.2.24 on 2021-08-05 14:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0235_auto_20210803_2020'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='office_name',
            field=models.TextField(blank=True, null=True),
        ),
    ]
