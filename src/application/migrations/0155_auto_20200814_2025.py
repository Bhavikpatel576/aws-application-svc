# Generated by Django 2.2 on 2020-08-14 20:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0154_auto_20200812_1430'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='cx_manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='application.CXManager'),
        ),
        migrations.AlterField(
            model_name='cxmanager',
            name='schedule_a_call_url',
            field=models.URLField(default='https://meetings.hubspot.com/homeward/homeward-intro-call'),
        ),
    ]