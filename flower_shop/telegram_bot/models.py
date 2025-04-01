from django.db import models
from django.contrib.auth.models import User


class TelegramMessage(models.Model):
    """Модель для хранения истории сообщений Telegram бота"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_messages')
    message_id = models.CharField(max_length=100)
    chat_id = models.CharField(max_length=100)
    message_text = models.TextField()
    is_from_user = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сообщение Telegram'
        verbose_name_plural = 'Сообщения Telegram'

    def __str__(self):
        return f"Message from {'user' if self.is_from_user else 'bot'} at {self.created_at}"


class TelegramNotification(models.Model):
    """Модель для хранения уведомлений, отправленных через Telegram"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_notifications')
    notification_type = models.CharField(max_length=50)  # order_status, promotion, etc.
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Уведомление Telegram'
        verbose_name_plural = 'Уведомления Telegram'

    def __str__(self):
        return f"{self.notification_type} notification for {self.user.username}"
