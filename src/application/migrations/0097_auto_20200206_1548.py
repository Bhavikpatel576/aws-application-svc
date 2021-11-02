# Generated by Django 2.2 on 2020-02-06 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0096_change_lender_add_mortgage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='category',
            field=models.CharField(choices=[('existing_property', 'existing_property'), ('real_estate_agent', 'real_estate_agent'), ('homeward_mortgage', 'homeward_mortgage'), ('mortgage_preapproval', 'mortgage_preapproval'), ('buying_situation', 'buying_situation'), ('photo_upload', 'photo_upload'), ('disclosures', 'disclosures')], max_length=50),
        ),
        migrations.AlterField(
            model_name='task',
            name='name',
            field=models.CharField(choices=[('existing_property', 'existing_property'), ('real_estate_agent', 'real_estate_agent'), ('mortgage_preapproval', 'mortgage_preapproval'), ('current_lender', 'current_lender'), ('buying_situation', 'buying_situation'), ('photo_upload', 'photo_upload'), ('disclosures', 'disclosures'), ('co_mortgage', 'co_mortgage')], max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='start_date',
            field=models.DateField(auto_now_add=True, null=True),
        ),
    ]