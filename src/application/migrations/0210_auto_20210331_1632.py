# Generated by Django 2.2 on 2021-03-31 16:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0209_application_apex_partner_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loan',
            name='blend_application_id',
            field=models.TextField(unique=True),
        ),
        migrations.AlterField(
            model_name='loan',
            name='salesforce_id',
            field=models.TextField(unique=True),
        ),
        migrations.AlterField(
            model_name='loan',
            name='status',
            field=models.TextField(blank=True, null=True),
        ),
    ]