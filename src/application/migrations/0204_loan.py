# Generated by Django 2.2 on 2021-03-23 20:29

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0203_auto_20210322_1606'),
    ]

    operations = [
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('blend_application_id', models.CharField(max_length=50, unique=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to='application.Application')),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
                ('salesforce_id', models.CharField(max_length=50, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('denial_reason', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
