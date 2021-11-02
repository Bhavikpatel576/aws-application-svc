# Generated by Django 2.2 on 2019-07-02 10:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('application', '0033_auto_20190628_0522'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketValuation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('property_condition', models.CharField(blank=True, choices=[('Poor', 'Poor'), ('Average', 'Average'), ('Excellent', 'Excellent')], max_length=50, null=True)),
                ('is_in_completed_neighborhood', models.BooleanField(blank=True, null=True)),
                ('is_less_than_one_acre', models.BooleanField(blank=True, null=True)),
                ('is_built_after_1960', models.BooleanField(blank=True, null=True)),
                ('current_home', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='application.CurrentHome')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MarketValueOpinion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('suggested_list_price', models.IntegerField(blank=True, null=True)),
                ('minimum_sales_price', models.IntegerField(blank=True, null=True)),
                ('maximum_sales_price', models.IntegerField(blank=True, null=True)),
                ('sales_price_confidence', models.CharField(choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], max_length=50)),
                ('estimated_days_on_market', models.CharField(blank=True, max_length=50, null=True)),
                ('type', models.CharField(choices=[('local_agent', 'local_agent'), ('sr_analyst', 'sr_analyst')], max_length=50)),
                ('market_valuation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='application.MarketValuation')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MarketValueOpinionComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('comment', models.TextField(blank=True, max_length=140, null=True)),
                ('is_favorite', models.BooleanField(default=False)),
                ('market_value_opinion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='application.MarketValueOpinion')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='marketvalueanalysiscomment',
            name='market_value_analysis',
        ),
        migrations.RemoveField(
            model_name='comparable',
            name='listing_id',
        ),
        migrations.RemoveField(
            model_name='comparable',
            name='market_value_analysis',
        ),
        migrations.RemoveField(
            model_name='comparable',
            name='mls',
        ),
        migrations.AddField(
            model_name='comparable',
            name='address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='application.Address'),
        ),
        migrations.AddField(
            model_name='comparable',
            name='verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='comparable',
            name='comparable_type',
            field=models.CharField(choices=[('Subject property', 'Subject property'), ('Primary', 'Primary'), ('Secondary', 'Secondary')], max_length=50),
        ),
        migrations.DeleteModel(
            name='MarketValueAnalysis',
        ),
        migrations.DeleteModel(
            name='MarketValueAnalysisComment',
        ),
        migrations.AddField(
            model_name='comparable',
            name='market_valuation',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='comparables', to='application.MarketValuation'),
            preserve_default=False,
        ),
    ]
