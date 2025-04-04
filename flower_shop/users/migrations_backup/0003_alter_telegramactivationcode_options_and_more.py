# Generated by Django 5.1.7 on 2025-03-31 04:57

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_telegram_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='telegramactivationcode',
            options={'ordering': ['-created_at']},
        ),
        migrations.AddField(
            model_name='profile',
            name='telegram_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='telegramactivationcode',
            index=models.Index(fields=['code'], name='users_teleg_code_f49825_idx'),
        ),
    ]
