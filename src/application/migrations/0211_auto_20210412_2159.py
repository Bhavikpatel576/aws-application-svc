# Generated by Django 2.2 on 2021-04-12 21:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0210_auto_20210331_1632'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='bathrooms',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True),
        ),
        migrations.AddField(
            model_name='offer',
            name='bedrooms',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True),
        ),
        migrations.AddField(
            model_name='offer',
            name='photo_url',
            field=models.TextField(blank=True, null=True),
        ),
    ]
