# Generated by Django 2.2 on 2020-03-10 16:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0111_auto_20200306_2334'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='realestateagent',
            name='required_sf_id_certified_agent',
        ),
        migrations.RemoveConstraint(
            model_name='realestateagent',
            name='required_phone_certified_agent',
        ),
        migrations.RemoveConstraint(
            model_name='realestateagent',
            name='required_email_certified_agent',
        ),
        migrations.AlterField(
            model_name='task',
            name='name',
            field=models.CharField(choices=[('existing_property', 'existing_property'), ('real_estate_agent', 'real_estate_agent'), ('my_lender', 'my_lender'), ('my_lender_better', 'my_lender_better'), ('buying_situation', 'buying_situation'), ('photo_upload', 'photo_upload'), ('disclosures', 'disclosures'), ('co_mortgage', 'co_mortgage'), ('tx_mortgage', 'tx_mortgage')], max_length=50, unique=True),
        ),
        migrations.AddConstraint(
            model_name='realestateagent',
            constraint=models.CheckConstraint(check=models.Q(('is_certified', False), models.Q(('phone__isnull', False), models.Q(_negated=True, phone='')), _connector='OR'), name='required_sf_id_certified_agent'),
        ),
        migrations.AddConstraint(
            model_name='realestateagent',
            constraint=models.CheckConstraint(check=models.Q(('is_certified', False), models.Q(('sf_id__isnull', False), models.Q(_negated=True, sf_id='')), _connector='OR'), name='required_phone_certified_agent'),
        ),
        migrations.AddConstraint(
            model_name='realestateagent',
            constraint=models.CheckConstraint(check=models.Q(('is_certified', False), models.Q(('email__isnull', False), models.Q(_negated=True, email='')), _connector='OR'), name='required_email_certified_agent'),
        ),
    ]
