# Generated by Django 2.2 on 2019-05-06 14:25

import application.models.models
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid

from application.models.application import HomeBuyingStage


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('street', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=255)),
                ('state', models.CharField(max_length=255)),
                ('zip', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='FloorPrice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.IntegerField()),
                ('expiration', models.DateTimeField(blank=True, default=None, null=True)),
                ('activation', models.DateTimeField(blank=True, default=None, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CurrentHome',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('market_value', models.IntegerField(blank=True, null=True)),
                ('close_date', models.DateTimeField(blank=True, default=None, null=True)),
                ('final_sales_price', models.IntegerField(blank=True, null=True)),
                ('outstanding_loan_amount', models.IntegerField(blank=True, null=True)),
                ('attributes', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='application.Address')),
                ('floor_price', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='application.FloorPrice')),
            ],
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('shopping_location', models.CharField(max_length=255)),
                ('home_buying_stage', models.CharField(choices=[(HomeBuyingStage('researching online'), 'researching online'), (HomeBuyingStage('viewing listings in person'), 'viewing listings in person'), (
                    HomeBuyingStage('making an offer'), 'making an offer'), (HomeBuyingStage('working with a builder'), 'working with a builder')], max_length=50)),
                ('stage', models.CharField(choices=['draft', 'complete'], max_length=50)),
                ('min_price', models.IntegerField(blank=True, null=True)),
                ('max_price', models.IntegerField(blank=True, null=True)),
                ('move_in', models.CharField(max_length=255)),
                ('start_date', models.DateTimeField(auto_now_add=True)),
                ('current_home', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='application.CurrentHome')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='application.Customer')),
            ],
        ),
    ]
