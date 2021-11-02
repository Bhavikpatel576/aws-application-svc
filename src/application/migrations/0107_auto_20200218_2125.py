# Generated by Django 2.2 on 2020-02-18 21:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0106_auto_20200218_1616'),
    ]

    operations = [
        migrations.AddField(
            model_name='builder',
            name='is_certified',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name='builder',
            name='sf_id',
            field=models.CharField(blank=True, default=None, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='realestateagent',
            name='is_certified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='realestateagent',
            name='sf_id',
            field=models.CharField(blank=True, default=None, max_length=50, null=True),
        ),
        migrations.AddConstraint(
            model_name='builder',
            constraint=models.UniqueConstraint(condition=models.Q(is_certified=True), fields=('representative_phone',), name='unique_phone_certified_builder'),
        ),
        migrations.AddConstraint(
            model_name='builder',
            constraint=models.UniqueConstraint(condition=models.Q(is_certified=True), fields=('sf_id',), name='unique_sf_id_certified_builder'),
        ),
        migrations.AddConstraint(
            model_name='builder',
            constraint=models.CheckConstraint(check=models.Q(('is_certified', False), ('representative_phone__isnull', False), _connector='OR'), name='required_sf_id_certified_builder'),
        ),
        migrations.AddConstraint(
            model_name='builder',
            constraint=models.CheckConstraint(check=models.Q(('is_certified', False), ('sf_id__isnull', False), _connector='OR'), name='required_phone_certified_builder'),
        ),
        migrations.AddConstraint(
            model_name='realestateagent',
            constraint=models.UniqueConstraint(condition=models.Q(is_certified=True), fields=('sf_id',), name='unique_sf_id_certified_agent'),
        ),
        migrations.AddConstraint(
            model_name='realestateagent',
            constraint=models.UniqueConstraint(condition=models.Q(is_certified=True), fields=('phone',), name='unique_phone_certified_agent'),
        ),
        migrations.AddConstraint(
            model_name='realestateagent',
            constraint=models.CheckConstraint(check=models.Q(('is_certified', False), ('phone__isnull', False), _connector='OR'), name='required_sf_id_certified_agent'),
        ),
        migrations.AddConstraint(
            model_name='realestateagent',
            constraint=models.CheckConstraint(check=models.Q(('is_certified', False), ('sf_id__isnull', False), _connector='OR'), name='required_phone_certified_agent'),
        ),
    ]
