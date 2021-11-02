# Generated by Django 2.2 on 2019-07-15 10:58

import application.models.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0039_auto_20190715_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='type',
            field=models.CharField(choices=[('application stage', 'application stage'), ('general', 'general')], default=application.models.models.NoteType('general'), max_length=50),
        ),
    ]
