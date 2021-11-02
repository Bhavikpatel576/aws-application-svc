# Generated by Django 2.2 on 2020-10-06 21:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0167_auto_20200928_2119'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='unit',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='currenthome',
            name='salesforce_id',
            field=models.CharField(blank=True, editable=False, max_length=255, null=True),
        ),
    ]