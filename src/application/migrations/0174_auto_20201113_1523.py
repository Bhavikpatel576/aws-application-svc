# Generated by Django 2.2 on 2020-11-13 15:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0173_auto_20201105_0200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rent',
            name='estimated_prepaid_rent',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
