# Generated by Django 5.1.4 on 2025-01-08 19:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_remove_profile_followers_delete_follow'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_premium',
            field=models.BooleanField(default=False),
        ),
    ]