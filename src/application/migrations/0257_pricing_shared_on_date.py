# Generated by Django 2.2.24 on 2021-10-06 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0256_newhomepurchase_customer_purchase_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricing',
            name='shared_on_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='shared on'),
        ),
    ]
