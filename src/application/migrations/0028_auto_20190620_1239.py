# Generated by Django 2.2 on 2019-06-20 12:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0027_auto_20190619_1248'),
    ]

    operations = [
        migrations.RenameField(
            model_name='preapproval',
            old_name='mortgage_amount',
            new_name='amount',
        ),
    ]