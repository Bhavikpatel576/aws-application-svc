# Generated by Django 2.2 on 2019-07-04 09:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0037_marketvaluereport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketvalueopinion',
            name='sales_price_confidence',
            field=models.CharField(blank=True, choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], max_length=50, null=True),
        ),
    ]