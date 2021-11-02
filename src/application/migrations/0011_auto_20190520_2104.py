# Generated by Django 2.2 on 2019-05-20 21:04

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0010_auto_20190520_1848'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='marketvalueanalysis',
            name='comment',
        ),
        migrations.AlterField(
            model_name='application',
            name='current_home',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='application', to='application.CurrentHome'),
        ),
        migrations.AlterField(
            model_name='application',
            name='stage',
            field=models.CharField(choices=[('draft', 'draft'), ('complete', 'complete'), ('mv submitted', 'mv submitted')], max_length=50),
        ),
        migrations.CreateModel(
            name='MarketValueAnalysisComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('comment', models.TextField(blank=True, max_length=140, null=True)),
                ('market_value_analysis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='application.MarketValueAnalysis')),
            ],
        ),
    ]
