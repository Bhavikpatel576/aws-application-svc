# Generated by Django 2.2.24 on 2021-10-07 17:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0255_merge_20210930_1758'),
    ]

    operations = [
        migrations.AddField(
            model_name='newhomepurchase',
            name='customer_purchase_status',
            field=models.TextField(blank=True, null=True),
        ),
    ]
