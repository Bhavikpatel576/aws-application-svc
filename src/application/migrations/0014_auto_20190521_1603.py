# Generated by Django 2.2 on 2019-05-21 16:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0013_auto_20190521_1509'),
    ]

    operations = [
        migrations.AlterField(
            model_name='currenthomeimage',
            name='current_home',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='application.CurrentHome'),
        ),
    ]
