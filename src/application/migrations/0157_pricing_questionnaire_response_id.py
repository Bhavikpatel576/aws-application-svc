# Generated by Django 2.2 on 2020-08-24 21:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0156_auto_20200819_1754'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricing',
            name='questionnaire_response_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
