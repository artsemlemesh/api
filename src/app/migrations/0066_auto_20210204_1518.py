# Generated by Django 3.0.6 on 2021-02-04 15:18

import app.models.user
from django.db import migrations
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0065_orderitem_reason'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='photo',
            field=sorl.thumbnail.fields.ImageField(blank=True, help_text='avatar photo', max_length=255, null=True, upload_to=app.models.user.get_upload_path),
        ),
    ]
