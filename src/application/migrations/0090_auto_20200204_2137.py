# Generated by Django 2.2 on 2020-02-04 21:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0089_auto_20200131_2220'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AcknowledgeableDocument',
            new_name='Disclosure',
        ),
        migrations.RenameField(
            model_name='acknowledgement',
            old_name='document',
            new_name='disclosure',
        ),
        migrations.RemoveField(
            model_name='taskstatus',
            name='task',
        ),
        migrations.AlterField(
            model_name='task',
            name='category',
            field=models.CharField(choices=[('existing_property', 'existing_property'), ('real_estate_agent', 'real_estate_agent'), ('mortgage_preapproval', 'mortgage_preapproval'), ('buying_situation', 'buying_situation'), ('photo_upload', 'photo_upload'), ('disclosures', 'disclosures')], max_length=50),
        ),
        migrations.AlterField(
            model_name='task',
            name='name',
            field=models.CharField(choices=[('existing_property', 'existing_property'), ('real_estate_agent', 'real_estate_agent'), ('mortgage_preapproval', 'mortgage_preapproval'), ('buying_situation', 'buying_situation'), ('photo_upload', 'photo_upload'), ('disclosures', 'disclosures')], max_length=50, unique=True),
        ),
    ]