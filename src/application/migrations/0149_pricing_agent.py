# Generated by Django 2.2 on 2020-07-29 21:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0148_application_agent_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricing',
            name='agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='application.RealEstateAgent'),
        ),
    ]
