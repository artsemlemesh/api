# Generated by Django 3.0.6 on 2021-12-18 06:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0085_orderitem_batch'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='batch',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='batch_id'),
        ),
    ]
