# Generated by Django 2.2 on 2019-06-17 20:58

import application.models.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0022_auto_20190611_0656'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='lead_status',
            field=models.CharField(choices=[('New', 'New'), ('Qualifying', 'Qualifying'), ('Nurture', 'Nurture'), ('Qualified', 'Qualified'), ('Archive', 'Archive'), ('Trash', 'Trash')], default=application.models.application.LeadStatus('New'), max_length=50),
        ),
    ]
