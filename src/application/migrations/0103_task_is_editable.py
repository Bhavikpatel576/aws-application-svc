# Generated by Django 2.2 on 2020-02-10 20:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0102_add_states_to_disclosures'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='is_editable',
            field=models.BooleanField(default=False),
        ),
    ]
