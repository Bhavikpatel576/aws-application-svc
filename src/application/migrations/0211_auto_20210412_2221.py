# Generated by Django 2.2 on 2021-04-12 22:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0210_auto_20210331_1632'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='preferred_closing_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='offer',
            name='other_offers',
            field=models.CharField(blank=True, choices=[('No', 'No'), ('Not sure', 'Not sure'), ('1-4', '1-4'), ('5+', '5+')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='offer',
            name='property_type',
            field=models.CharField(blank=True, choices=[('Single Family', 'Single Family'), ('Multi-Family', 'Multi-Family'), ('Luxury', 'Luxury'), ('Condo', 'Condo'), ('Lot', 'Lot'), ('Other', 'Other')], max_length=50, null=True),
        ),
    ]