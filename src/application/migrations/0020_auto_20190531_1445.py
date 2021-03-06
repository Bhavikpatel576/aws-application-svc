# Generated by Django 2.2 on 2019-05-31 14:45

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0019_realestateagent_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='address',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='hubspot_context',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='hubspot_error_retry_count',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='application',
            name='pushed_to_hubspot_on',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='pushed_to_salesforce_on',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='salesforce',
            field=models.CharField(blank=True, editable=False, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='sf_error_retry_count',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='application',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='utm',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name='builder',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='builder',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='comparable',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='comparable',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='currenthome',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='currenthome',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='currenthomeimage',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='currenthomeimage',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='floorprice',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='floorprice',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='marketvalueanalysis',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='marketvalueanalysis',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='marketvalueanalysiscomment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='marketvalueanalysiscomment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='mortgagelender',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='mortgagelender',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='realestateagent',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='realestateagent',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, null=True),
        ),
    ]
