# Generated by Django 2.2 on 2020-12-28 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0181_auto_20201223_1849'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricing',
            name='max_price',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='pricing',
            name='min_price',
            field=models.PositiveIntegerField(),
        ),
    ]