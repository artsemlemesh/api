# Generated by Django 3.0.6 on 2020-09-30 08:31

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0042_shipment_moved_to_order_n_remove_payment'),
    ]

    operations = [
        migrations.CreateModel(
            name='ByndePayment',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(
                    default=django.utils.timezone.now, editable=False,
                    verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(
                    default=django.utils.timezone.now, editable=False,
                    verbose_name='modified')),
                ('order', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payment', to='app.Order')),
                ('payment_intent', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payment', to='djstripe.PaymentIntent')),
            ],
            options={
                'verbose_name': 'payment',
                'ordering': ('-modified',),
            },
        ),
    ]
