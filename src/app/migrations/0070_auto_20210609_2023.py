# Generated by Django 3.0.6 on 2021-06-09 20:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0069_auto_20210607_0927'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appleloginserialzerbaseextends',
            name='appleId',
        ),
        migrations.RemoveField(
            model_name='appleloginserialzermodel',
            name='appleId',
        ),
        migrations.AddField(
            model_name='appleloginserialzermodel',
            name='user',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='AppleLoginSerialzerBase',
        ),
        migrations.DeleteModel(
            name='AppleLoginSerialzerBaseExtends',
        ),
    ]
