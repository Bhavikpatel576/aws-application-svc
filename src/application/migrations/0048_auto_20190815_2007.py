# Generated by Django 2.2 on 2019-08-15 20:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0047_merge_20190812_0552'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='new_salesforce',
            field=models.CharField(blank=True, editable=False, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='self_reported_referral_source',
            field=models.CharField(blank=True, choices=[('my_agent', 'my_agent'), ('my_loan_officer', 'my_loan_officer'), ('my_home_builder', 'my_home_builder'), ('a_friend', 'a_friend'), ('online_ad', 'online_ad'), ('radio', 'radio'), ('sign_in_yard', 'sign_in_yard'), ('other', 'other'), ('none', 'none')], max_length=255, null=True),
        ),
    ]
