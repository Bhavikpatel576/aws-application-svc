# Generated by Django 2.2 on 2019-05-23 06:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0016_merge_20190522_0656'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='offer_property_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='application.Address'),
        ),
    ]
