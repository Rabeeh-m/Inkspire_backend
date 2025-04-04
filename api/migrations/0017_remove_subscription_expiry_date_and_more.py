# Generated by Django 5.1.4 on 2025-01-11 19:06

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_remove_subscription_is_active_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscription',
            name='expiry_date',
        ),
        migrations.AddField(
            model_name='subscription',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('expired', 'Expired')], default='', max_length=50),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='start_date',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
