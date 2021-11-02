# Generated by Django 2.2 on 2019-06-18 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0023_application_lead_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketvalueanalysis',
            name='mls',
            field=models.CharField(blank=True, choices=[('GA_FMLS', 'GA_FMLS'), ('GA_MLS', 'GA_MLS'), ('TX_SABOR', 'TX_SABOR'), ('TX_HAR', 'TX_HAR'), ('TX_ACTRIS', 'TX_ACTRIS'), ('TX_NTREIS', 'TX_NTREIS'), ('CO_Metrolist', 'CO_Metrolist'), ('CO_IRES', 'CO_IRES')], max_length=50, null=True),
        ),
    ]
