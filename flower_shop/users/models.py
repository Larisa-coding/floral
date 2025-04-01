from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    # Поля для телеграм
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True)
    telegram_id = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"

    def save(self, *args, **kwargs):
        # Синхронизируем telegram_id и telegram_chat_id
        if hasattr(self, 'telegram_id') and hasattr(self, 'telegram_chat_id'):
            if self.telegram_id and not self.telegram_chat_id:
                self.telegram_chat_id = str(self.telegram_id)
            elif self.telegram_chat_id and not self.telegram_id:
                try:
                    self.telegram_id = int(self.telegram_chat_id)
                except (ValueError, TypeError):
                    pass
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Создает или обновляет профиль пользователя при сохранении модели User"""
    if created:
        # Если пользователь только что создан, создаем новый профиль
        Profile.objects.create(user=instance)
    else:
        # Если пользователь обновлен, убеждаемся что профиль существует
        # и сохраняем его для применения логики синхронизации полей telegram_id и telegram_chat_id
        profile, created = Profile.objects.get_or_create(user=instance)
        if not created:
            profile.save()


class TelegramActivationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Добавляем индекс для ускорения поиска по коду
        indexes = [
            models.Index(fields=['code']),
        ]
        # Автоматическое удаление старых кодов активации
        ordering = ['-created_at']

    def __str__(self):
        return f"Код активации для {self.user.username}"