# Generated by Django 3.0.6 on 2020-08-07 02:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0015_remove_original_listing_item_image_columns'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='back_image',
            new_name='back_image_large',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='front_image',
            new_name='front_image_large',
        ),
    ]
