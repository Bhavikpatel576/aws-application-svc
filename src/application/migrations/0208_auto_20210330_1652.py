# Generated by Django 2.2 on 2021-03-30 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0207_auto_20210330_1558'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='home_list_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True),
        ),
        migrations.AlterField(
            model_name='offer',
            name='offer_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True),
        ),
    ]
