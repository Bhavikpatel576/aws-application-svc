# Generated by Django 2.2 on 2019-07-02 11:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0035_auto_20190702_1055'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketvalueopinion',
            name='market_valuation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='value_opinions', to='application.MarketValuation'),
        ),
    ]
