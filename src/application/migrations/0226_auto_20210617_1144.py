# Generated by Django 2.2 on 2021-06-17 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0225_merge_20210603_1702'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='base_convenience_fee',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='loan',
            name='estimated_broker_convenience_fee_credit',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='loan',
            name='estimated_convenience_fee_discount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
