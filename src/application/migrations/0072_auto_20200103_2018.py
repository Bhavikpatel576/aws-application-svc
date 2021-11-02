# Generated by Django 2.2 on 2020-01-03 20:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0070_auto_20191223_1655'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='buying_agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='buying_agent', to='application.RealEstateAgent'),
        ),
        migrations.AlterField(
            model_name='application',
            name='listing_agent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='listing_agent', to='application.RealEstateAgent'),
        ),
    ]