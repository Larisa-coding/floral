import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from django.conf import settings
from users.models import TelegramActivationCode, Profile
from orders.models import Order

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        await update.message.reply_html(
            f"Привет, {user.mention_html()}! 👋\n\n"
            f"Я бот цветочного магазина. Через меня вы сможете получать уведомления о статусе ваших заказов.\n\n"
            f"Чтобы подключить ваш аккаунт, пожалуйста, отправьте мне код активации, который вы получили на сайте."
        )

    # ... [остальные методы бота]

    def setup(self):
        """Настройка бота"""
        try:
            # Создаем приложение с токеном
            self.application = Application.builder().token(self.token).build()

            # Добавляем обработчики команд
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("orders", self.orders_command))
            self.application.add_handler(CommandHandler("disconnect", self.disconnect_command))

            # Обработчик текстовых сообщений (для кода активации)
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_activation_code))

            # Обработчик ошибок
            self.application.add_error_handler(self.error_handler)

            logger.info("Бот настроен и готов к запуску")
            return True
        except Exception as e:
            logger.error(f"Ошибка при настройке бота: {e}")
            return False

    def start(self):
        """Запуск бота"""
        if self.application:
            asyncio.run(self.application.run_polling())

    def notify_new_order(self, order):
        """Отправка уведомления о новом заказе"""
        try:
            if order.user.profile.telegram_chat_id:
                chat_id = order.user.profile.telegram_chat_id

                # Формируем список товаров в заказе
                items_text = ""
                for item in order.items.all():
                    items_text += f"- {item.product.name} x {item.quantity} = {item.total_price()} ₽\n"

                message = (
                    f"🎉 <b>Ваш заказ успешно оформлен!</b>\n\n"
                    f"📦 <b>Заказ №{order.order_number}</b>\n\n"
                    f"<b>Товары:</b>\n{items_text}\n"
                    f"Подытог: {order.subtotal} ₽\n"
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

    # ... [другие методы уведомлений]


# Создаем экземпляр бота
bot = TelegramBot()


def start_bot():
    """Функция для запуска бота"""
    if bot.setup():
        bot.start()