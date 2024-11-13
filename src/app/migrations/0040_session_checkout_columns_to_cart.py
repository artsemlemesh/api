# Generated by Django 3.0.6 on 2020-09-28 08:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0039_merge_20200926_1355'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='order_id',
            field=models.UUIDField(
                blank=True, null=True, verbose_name='order id candidate'),
        ),
        migrations.AddField(
            model_name='cart',
            name='stripe_payment_intent_id',
            field=models.CharField(
                blank=True, max_length=48, null=True,
                verbose_name='stripe payment intent id'),
        ),
        migrations.AddField(
            model_name='cart',
            name='stripe_session_id',
            field=models.CharField(
                blank=True, max_length=80, null=True,
                verbose_name='stripe session id'),
        ),
    ]
