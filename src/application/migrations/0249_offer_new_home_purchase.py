# Generated by Django 2.2.24 on 2021-09-14 18:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0248_merge_20210913_2132'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='new_home_purchase',
            field=models.OneToOneField(blank=True, null=True, related_name='offer', on_delete=django.db.models.deletion.CASCADE, to='application.NewHomePurchase'),
        ),
    ]
