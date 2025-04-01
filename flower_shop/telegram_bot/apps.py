from django.apps import AppConfig
from django.conf import settings
import logging
import sys

logger = logging.getLogger(__name__)


class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_bot'

    def ready(self):
        if 'runserver' not in sys.argv:
            return

        if settings.TELEGRAM_BOT_TOKEN:
            try:
                from .bot import init_bot, start_bot_polling
                # Только инициализируем бота, но не запускаем его
                if init_bot():
                    logger.info("Telegram bot initialized successfully")
                    # Запускаем бота в отдельном потоке
                    if start_bot_polling():
                        logger.info("Telegram bot polling started successfully")
                    else:
                        logger.warning("Telegram bot polling not started")
                else:
                    logger.error("Failed to initialize Telegram bot")
            except Exception as e:
                logger.error(f"Error initializing Telegram bot: {e}")