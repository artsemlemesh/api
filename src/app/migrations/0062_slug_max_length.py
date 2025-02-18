# Generated by Django 3.0.6 on 2021-01-14 18:36

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0061_productbrand_suggested'),
    ]

    operations = [
        migrations.AlterField(
            model_name='listing',
            name='platform_fee_pct',
            field=models.DecimalField(blank=True, decimal_places=4, default=1, help_text='platform fee percent from 0 to 10', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(40)]),
        ),
        migrations.AlterField(
            model_name='listing',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='productbrand',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='productcategory',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='productsize',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True),
        ),
    ]
