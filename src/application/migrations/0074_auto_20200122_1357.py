# Generated by Django 2.2 on 2020-01-22 13:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0073_auto_20200116_2204'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='home_buying_stage',
            field=models.CharField(choices=[('researching online', 'researching online'), ('viewing listings in person', 'viewing listings in person'), ('making an offer', 'making an offer'), ('working with a builder', 'working with a builder'), ('already in contract', 'already in contract')], max_length=50),
        ),
        migrations.AlterField(
            model_name='realestatelead',
            name='home_buying_stage',
            field=models.CharField(choices=[('researching online', 'researching online'), ('viewing listings in person', 'viewing listings in person'), ('making an offer', 'making an offer'), ('working with a builder', 'working with a builder'), ('already in contract', 'already in contract')], max_length=50),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_statuses', to='application.Application'),
        ),
    ]
