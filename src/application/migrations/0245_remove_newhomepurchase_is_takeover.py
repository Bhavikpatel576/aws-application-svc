# Generated by Django 2.2.24 on 2021-09-10 13:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0244_application_filter_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='newhomepurchase',
            name='is_takeover',
        ),
    ]