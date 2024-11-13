# Generated by Django 3.0.6 on 2021-12-13 11:56

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0073_remove_product_circleci'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuggestedProductBrand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('slug', models.SlugField(blank=True, max_length=255, null=True)),
                ('suggested', models.BooleanField(default=False, verbose_name='is suggested')),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='app.SuggestedProductBrand')),
            ],
            options={
                'verbose_name': 'Suggested Product Brand',
                'verbose_name_plural': 'Suggested Product Brands',
            },
        ),
    ]
