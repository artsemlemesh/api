# Generated by Django 3.0.6 on 2020-09-28 10:29

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0040_session_checkout_columns_to_cart'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(
                    default=django.utils.timezone.now,
                    editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(
                    default=django.utils.timezone.now, editable=False,
                    verbose_name='modified')),
                ('platform_order_id', models.UUIDField(
                    unique=True, verbose_name='platform order id')),
                ('customer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='orders', to='app.ByndeCustomer',
                    verbose_name='customer')),
                ('payment_intent', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='order', to='djstripe.PaymentIntent',
                    verbose_name='stripe payment intent')),
            ],
            options={
                'verbose_name': 'order',
                'ordering': ('-modified',),
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
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
                ('listing', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='order_item', to='app.Listing',
                    verbose_name='listing')),
                ('order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='order_items', to='app.Order',
                    verbose_name='order')),
            ],
            options={
                'verbose_name': 'order',
                'ordering': ('order', '-modified'),
                'unique_together': {('order', 'listing')},
            },
        ),
    ]
