# Generated by Django 2.2 on 2020-03-31 18:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0112_auto_20200310_1655'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='questionnaire_response_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]