# Generated by Django 2.2 on 2019-07-15 20:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0040_note_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='lead_source',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='lead_source_drill_down_1',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='lead_source_drill_down_2',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
