# Generated by Django 2.2 on 2020-06-03 20:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0118_offer_accepted_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='newhomepurchase',
            name='homeward_purchase_close_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='newhomepurchase',
            name='option_period_end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
