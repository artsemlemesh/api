# Generated by Django 3.0.6 on 2022-01-10 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0088_auto_20211229_1202'),
    ]

    operations = [
        migrations.AddField(
            model_name='shipmenttracker',
            name='tracking_url',
            field=models.CharField(max_length=20, null=True, verbose_name='tracking url'),
        ),
    ]
