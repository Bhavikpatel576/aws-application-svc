# Generated by Django 2.2 on 2021-02-11 17:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0188_application_agent_client_contact_preference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='cx_manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cx_manager', to='application.CXManager'),
        ),
        migrations.RenameModel(
            old_name='CXManager',
            new_name='InternalSupportUser',
        ),
        migrations.AddField(
            model_name='application',
            name='loan_advisor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='loan_advisor', to='application.InternalSupportUser'),
        ),
        migrations.AlterField(
            model_name='application',
            name='cx_manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cx_manager', to='application.InternalSupportUser'),
        ),
    ]
