# Generated by Django 2.2 on 2021-03-12 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0200_offer_offer_property_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='status',
            field=models.TextField(default='Incomplete'),
        ),
    ]
