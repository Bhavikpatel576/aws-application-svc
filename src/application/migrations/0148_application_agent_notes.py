# Generated by Django 2.2 on 2020-07-28 22:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0147_pricing_agent_remarks'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='agent_notes',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
