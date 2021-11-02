# Generated by Django 2.2 on 2020-02-18 16:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0105_disclosure_active'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='taskstatus',
            constraint=models.UniqueConstraint(fields=('task_obj', 'application'), name='unique_taskstatus'),
        ),
    ]
