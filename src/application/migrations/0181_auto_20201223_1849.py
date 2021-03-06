# Generated by Django 2.2 on 2020-12-23 18:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0180_auto_20201222_2103'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricing',
            name='estimated_max_rent_amount',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='pricing',
            name='estimated_min_rent_amount',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
    ]
