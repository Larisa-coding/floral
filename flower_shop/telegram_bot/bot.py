import asyncio
import logging
import os
import sys
import django
import threading

# Настраиваем логирование перед всем остальным
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Определяем, запущен ли скрипт напрямую
STANDALONE_MODE = __name__ == '__main__'

# Инициализируем Django, если скрипт запущен отдельно
if STANDALONE_MODE:
    logger.info("Бот запущен в автономном режиме, инициализируем Django...")
    # Настраиваем переменную окружения для Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_shop.settings')
    # Инициализируем Django
    django.setup()
    logger.info("Django успешно инициализирован")

# Импорт настроек Django (после инициализации Django, если в автономном режиме)
from django.conf import settings

# Импорт телеграм-зависимостей с обработкой исключений
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

    TELEGRAM_AVAILABLE = True
    logger.info("Библиотека python-telegram-bot успешно импортирована")
except ImportError as e:
    TELEGRAM_AVAILABLE = False
    logger.error(f"Не удалось импортировать библиотеку python-telegram-bot: {e}")


    # Создаем заглушки для типов телеграма
    class Update:
        pass


    class ContextTypes:
        DEFAULT_TYPE = None

# Импорт моделей с обработкой исключений
try:
    from users.models import TelegramActivationCode, Profile
    from orders.models import Order

    MODELS_AVAILABLE = True
    logger.info("Модели Django успешно импортированы")
except (ImportError, ModuleNotFoundError) as e:
    MODELS_AVAILABLE = False
    logger.error(f"Не удалось импортировать модели Django: {e}")


class TelegramBot:
    _instance = None
    _is_running = False
    _application = None
    _token = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramBot, cls).__new__(cls)
            cls._instance._token = settings.TELEGRAM_BOT_TOKEN
            cls._instance._application = None
        return cls._instance

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        await update.message.reply_html(
            f"Привет, {user.mention_html()}! 👋\n\n"
            f"Я бот цветочного магазина. Через меня вы сможете получать уведомления о статусе ваших заказов.\n\n"
            f"Чтобы подключить ваш аккаунт, пожалуйста, отправьте мне код активации, который вы получили на сайте."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        await update.message.reply_text(
            "Список доступных команд:\n"
            "/start - Начать взаимодействие с ботом\n"
            "/help - Показать справку\n"
            "/orders - Показать ваши последние заказы\n"
            "/disconnect - Отключить бота от вашего аккаунта\n\n"
            "Для подключения бота к вашему аккаунту, просто отправьте мне код активации, который вы получили на сайте."
        )

    async def orders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /orders"""
        chat_id = update.effective_chat.id

        # Проверяем, привязан ли пользователь
        try:
            # Ищем пользователя как по telegram_chat_id, так и по telegram_id
            profile = None
            try:
                profile = Profile.objects.get(telegram_chat_id=str(chat_id))
            except Profile.DoesNotExist:
                # Пробуем найти по telegram_id
                try:
                    profile = Profile.objects.get(telegram_id=chat_id)
                except Profile.DoesNotExist:
                    pass

            if not profile:
                await update.message.reply_text(
                    "Ваш Telegram не привязан к аккаунту магазина. "
                    "Пожалуйста, перейдите на сайт и получите код активации в разделе профиля."
                )
                return

            # Получаем последние заказы пользователя
            orders = Order.objects.filter(user=profile.user).order_by('-created_at')[:5]

            if orders:
                response = "Ваши последние заказы:\n\n"
                for order in orders:
                    response += f"📦 Заказ #{order.order_number}\n"
                    response += f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    response += f"Статус: {order.get_status_display()}\n"
                    response += f"Сумма: {order.total} ₽\n\n"

                site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                keyboard = [[InlineKeyboardButton("Перейти к заказам на сайте", url=f"{site_url}/orders/my-orders/")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(response, reply_markup=reply_markup)
            else:
                await update.message.reply_text("У вас пока нет заказов.")
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды orders: {e}")
            await update.message.reply_text(
                "Произошла ошибка при получении списка заказов. "
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )

    async def disconnect_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /disconnect"""
        chat_id = update.effective_chat.id

        try:
            profile = Profile.objects.get(telegram_chat_id=str(chat_id))
            username = profile.user.username

            # Отвязываем Telegram
            profile.telegram_chat_id = None
            profile.telegram_username = None
            profile.save()

            await update.message.reply_text(
                f"Ваш аккаунт {username} отвязан от бота. "
                f"Вы больше не будете получать уведомления о заказах.\n\n"
                f"Если вы захотите снова подключить уведомления, перейдите в раздел профиля на сайте."
            )
        except Profile.DoesNotExist:
            await update.message.reply_text("Ваш Telegram не привязан к аккаунту магазина.")

    async def handle_activation_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик активационного кода"""
        code = update.message.text.strip()
        user = update.effective_user
        chat_id = update.effective_chat.id

        # Добавить явный ответ на любое текстовое сообщение
        await update.message.reply_text(f"Проверяю код: {code}...")

        logger.info(f"Получен возможный код активации: {code} от пользователя {user.username} (chat_id: {chat_id})")

        # Добавим поиск с игнорированием регистра и пробелов
        try:
            # Проверяем код активации
            logger.info(f"Поиск кода активации {code} в базе данных")

            # Пробуем найти с учетом регистра
            try:
                activation = TelegramActivationCode.objects.get(code=code)
            except TelegramActivationCode.DoesNotExist:
                # Если не нашли, ищем без учета регистра
                activation = TelegramActivationCode.objects.filter(code__iexact=code.strip()).first()
                if not activation:
                    raise TelegramActivationCode.DoesNotExist()

            logger.info(f"Код найден для пользователя {activation.user.username}")

            # Обновляем профиль пользователя
            profile = activation.user.profile
            profile.telegram_chat_id = str(chat_id)
            profile.telegram_username = user.username
            profile.save()
            logger.info(f"Профиль пользователя {activation.user.username} обновлен")

            # Удаляем использованный код
            activation.delete()
            logger.info(f"Код активации {code} удален")

            await update.message.reply_text(
                f"✅ Ваш Telegram успешно привязан к аккаунту {activation.user.username}!\n\n"
                f"Теперь вы будете получать уведомления о статусе ваших заказов."
            )
        except TelegramActivationCode.DoesNotExist:
            logger.warning(f"Код активации {code} не найден в базе данных")
            await update.message.reply_text(
                "❌ Неверный код активации или срок его действия истек.\n\n"
                "Пожалуйста, перейдите на сайт и получите новый код активации в разделе профиля."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке кода активации {code}: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке кода активации.\n\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error} при обработке {update}")

    def setup(self):
        """Настройка бота"""
        if not TELEGRAM_AVAILABLE:
            logger.warning("Библиотека python-telegram-bot не установлена")
            return False

        if not MODELS_AVAILABLE:
            logger.warning("Необходимые модели недоступны")
            return False

        # Если приложение уже настроено, не нужно настраивать повторно
        if self._application:
            logger.info("Бот уже настроен")
            return True

        try:
            # Создаем приложение с токеном
            self._application = Application.builder().token(self._token).build()

            # Сначала добавляем обработчик текстовых сообщений (приоритет важен!)
            self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_activation_code))

            # Затем добавляем обработчики команд
            self._application.add_handler(CommandHandler("start", self.start_command))
            self._application.add_handler(CommandHandler("help", self.help_command))
            self._application.add_handler(CommandHandler("orders", self.orders_command))
            self._application.add_handler(CommandHandler("disconnect", self.disconnect_command))

            # Обработчик ошибок
            self._application.add_error_handler(self.error_handler)

            logger.info("Бот настроен и готов к запуску")
            return True
        except Exception as e:
            logger.error(f"Ошибка при настройке бота: {e}")
            return False

    def start(self):
        """Запуск бота"""
        if self._application and not TelegramBot._is_running:
            # Проверяем, не запущен ли уже бот где-то еще
            try:
                import requests
                response = requests.get(f"https://api.telegram.org/bot{self._token}/getUpdates",
                                        params={"limit": 1, "timeout": 1})
                if response.status_code != 200:
                    logger.warning(f"Не удалось проверить статус бота: {response.status_code} {response.text}")
                    return False
            except Exception as e:
                logger.warning(f"Ошибка при проверке статуса бота: {e}")

            TelegramBot._is_running = True
            try:
                logger.info("Запускаем поллинг бота...")
                # Запускаем в отдельном потоке, чтобы не блокировать основной поток выполнения
                bot_thread = threading.Thread(target=self._run_bot_polling)
                bot_thread.daemon = True  # Поток завершится, когда основной поток завершится
                bot_thread.start()
                return True
            except Exception as e:
                TelegramBot._is_running = False
                logger.error(f"Ошибка при запуске бота: {e}")
                return False
        return False

    def _run_bot_polling(self):
        """Запускает поллинг бота в отдельном потоке"""
        try:
            # Используем event loop из asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._application.run_polling(drop_pending_updates=True))
        except Exception as e:
            logger.error(f"Ошибка в потоке бота: {e}")
        finally:
            TelegramBot._is_running = False
            logger.info("Бот остановлен")

    def stop(self):
        """Остановка бота"""
        if self._application and TelegramBot._is_running:
            try:
                asyncio.run(self._application.stop())
                TelegramBot._is_running = False
                logger.info("Бот остановлен")
                return True
            except Exception as e:
                logger.error(f"Ошибка при остановке бота: {e}")
        return False

    @property
    def application(self):
        """Получение экземпляра приложения бота"""
        return self._application

    def send_notification(self, chat_id, message):
        """Отправка уведомления пользователю"""

        async def send():
            try:
                await self._application.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                return True
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления: {e}")
                return False

        if self._application:
            return asyncio.run(send())
        return False

    def notify_order_status_change(self, order, previous_status):
        """Отправка уведомления об изменении статуса заказа"""
        try:
            # Проверяем, существует ли у пользователя профиль и telegram_chat_id
            if hasattr(order.user, 'profile') and getattr(order.user.profile, 'telegram_chat_id', None):
                chat_id = order.user.profile.telegram_chat_id

                # Получаем словарь статусов заказа безопасным способом
                try:
                    from orders.models import Order as OrderModel
                    status_dict = dict(OrderModel.STATUS_CHOICES)
                    prev_status_display = status_dict.get(previous_status, 'Неизвестно')
                except Exception:
                    prev_status_display = previous_status

                message = (
                    f"🔔 <b>Статус вашего заказа изменен!</b>\n\n"
                    f"📦 <b>Заказ №{order.order_number}</b>\n"
                    f"Статус изменен: <b>{order.get_status_display()}</b>\n"
                    f"Предыдущий статус: {prev_status_display}\n\n"
                    f"Сумма заказа: <b>{order.total} ₽</b>\n"
                    f"Дата заказа: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Спасибо, что выбрали наш магазин цветов! 🌹"
                )

                return self.send_notification(chat_id, message)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о смене статуса заказа: {e}")
        return False

    def notify_new_order(self, order):
        """Отправка уведомления о новом заказе"""
        try:
            # Проверяем, существует ли у пользователя профиль и telegram_chat_id
            if hasattr(order.user, 'profile') and getattr(order.user.profile, 'telegram_chat_id', None):
                chat_id = order.user.profile.telegram_chat_id

                # Формируем список товаров в заказе, безопасно получаем связанные элементы
                try:
                    items = order.items.all()
                    items_text = ""
                    for item in items:
                        items_text += f"- {item.product.name} x {item.quantity} = {item.total_price()} ₽\n"
                except Exception as e:
                    logger.warning(f"Ошибка при формировании списка товаров: {e}")
                    items_text = "Товары в заказе\n"

                message = (
                    f"🎉 <b>Ваш заказ успешно оформлен!</b>\n\n"
                    f"📦 <b>Заказ №{order.order_number}</b>\n\n"
                    f"<b>Товары:</b>\n{items_text}\n"
                    f"Доставка: {order.shipping_cost} ₽\n"
                    f"<b>Итого: {order.total} ₽</b>\n\n"
                    f"Статус: <b>{order.get_status_display()}</b>\n"
                    f"Дата заказа: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Мы уведомим вас об изменении статуса заказа.\n"
                    f"Спасибо, что выбрали наш магазин цветов! 🌹"
                )

                return self.send_notification(chat_id, message)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о новом заказе: {e}")
        return False

    def send_custom_notification(self, order, message_text):
        """Отправка произвольного уведомления пользователю"""
        try:
            # Проверяем, существует ли у пользователя профиль и telegram_chat_id
            if hasattr(order.user, 'profile') and getattr(order.user.profile, 'telegram_chat_id', None):
                chat_id = order.user.profile.telegram_chat_id

                message = (
                    f"📢 <b>Уведомление о заказе №{order.order_number}</b>\n\n"
                    f"{message_text}\n\n"
                    f"С уважением,\nКоманда цветочного магазина 🌹"
                )

                return self.send_notification(chat_id, message)
        except Exception as e:
            logger.error(f"Ошибка при отправке произвольного уведомления: {e}")
        return False


# Создаем экземпляр бота
bot = TelegramBot()


def init_bot():
    """Инициализирует бота для использования в приложении Django"""
    # Только настраиваем бота, не запускаем
    success = bot.setup()
    if success:
        logger.info("Бот инициализирован для использования в Django")
    return success


def start_bot_polling():
    """Запускает бота в режиме поллинга в отдельном потоке"""
    if bot.setup():
        return bot.start()
    return False


def stop_bot():
    """Останавливает бота"""
    return bot.stop()


def send_order_notification(order_id):
    """Отправляет уведомление о новом заказе"""
    try:
        from orders.models import Order
        order = Order.objects.get(id=order_id)
        return bot.notify_new_order(order)
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о новом заказе: {e}")
        return False


def send_status_update_notification(order_id, previous_status=None):
    """Отправляет уведомление об изменении статуса заказа"""
    try:
        from orders.models import Order
        order = Order.objects.get(id=order_id)
        # Если предыдущий статус не указан, используем текущий
        prev_status = previous_status if previous_status is not None else order.status
        return bot.notify_order_status_change(order, prev_status)
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о смене статуса заказа: {e}")
        return False


def send_custom_notification(order_id, message):
    """Отправляет произвольное уведомление клиенту"""
    try:
        from orders.models import Order
        order = Order.objects.get(id=order_id)
        return bot.send_custom_notification(order, message)
    except Exception as e:
        logger.error(f"Ошибка при отправке произвольного уведомления: {e}")
        return False


# Запускаем бота только если скрипт запущен напрямую
if __name__ == '__main__':
    try:
        logger.info("Запуск бота в автономном режиме...")
        if start_bot_polling():
            logger.info("Бот успешно запущен в фоновом режиме")

            # Чтобы скрипт не завершался сразу
            import time

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_bot()
                logger.info("Бот остановлен вручную")
        else:
            logger.warning("Не удалось запустить бота")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")