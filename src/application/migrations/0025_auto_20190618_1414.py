# Generated by Django 2.2 on 2019-06-18 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0024_auto_20190618_1344'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketvalueanalysis',
            name='property_condition',
            field=models.CharField(choices=[('Poor', 'Poor'), ('Average', 'Average'), ('Excellent', 'Excellent')], max_length=50),
        ),
    ]