from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from users.models import TelegramActivationCode, Profile
from orders.models import Order
import uuid
import logging

logger = logging.getLogger(__name__)


@login_required
def connect_telegram(request):
    """Генерация кода активации для подключения Telegram"""
    try:
        # Проверяем, не подключен ли уже Telegram
        if request.user.profile.telegram_chat_id:
            messages.warning(request, 'Telegram уже подключен к вашему аккаунту.')
            return redirect('profile')

        # Удаляем старые коды активации
        TelegramActivationCode.objects.filter(user=request.user).delete()

        # Генерируем новый код
        activation_code = str(uuid.uuid4())[:8]
        TelegramActivationCode.objects.create(
            user=request.user,
            code=activation_code
        )

        context = {
            'activation_code': activation_code,
            'bot_username': settings.TELEGRAM_BOT_USERNAME
        }
        return render(request, 'users/connect_telegram.html', context)
    except Exception as e:
        logger.error(f'Ошибка при генерации кода активации Telegram: {e}')
        messages.error(request, 'Произошла ошибка. Пожалуйста, попробуйте позже.')
        return redirect('profile')


@login_required
def disconnect_telegram(request):
    """Отключение Telegram от аккаунта"""
    try:
        profile = request.user.profile
        if profile.telegram_chat_id:
            profile.telegram_chat_id = None
            profile.telegram_username = None
            profile.save()
            messages.success(request, 'Telegram успешно отключен от вашего аккаунта.')
        else:
            messages.info(request, 'Telegram не был подключен к вашему аккаунту.')
        return redirect('profile')
    except Exception as e:
        logger.error(f'Ошибка при отключении Telegram: {e}')
        messages.error(request, 'Произошла ошибка. Пожалуйста, попробуйте позже.')
        return redirect('profile')


@login_required
def get_order_details(request, order_id):
    """API для получения деталей заказа через Telegram"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order_items = order.items.all()

        items_data = [{
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': float(item.price),
            'total': float(item.total_price())
        } for item in order_items]

        data = {
            'order_number': order.order_number,
            'status': order.get_status_display(),
            'created_at': order.created_at.strftime('%d.%m.%Y %H:%M'),
            'shipping_address': {
                'address': order.address,
                'city': order.city,
                'postal_code': order.postal_code,
                'country': order.country
            },
            'items': items_data,
            'subtotal': float(order.subtotal),
            'shipping_cost': float(order.shipping_cost),
            'total': float(order.total)
        }
        return JsonResponse(data)
    except Exception as e:
        logger.error(f'Ошибка при получении деталей заказа: {e}')
        return JsonResponse({'error': 'Произошла ошибка при получении деталей заказа'}, status=400)


@login_required
def check_telegram_status(request):
    """Проверка статуса подключения Telegram"""
    try:
        profile = request.user.profile
        return JsonResponse({
            'is_connected': bool(profile.telegram_chat_id),
            'username': profile.telegram_username
        })
    except Exception as e:
        logger.error(f'Ошибка при проверке статуса Telegram: {e}')
        return JsonResponse({'error': 'Произошла ошибка при проверке статуса'}, status=400)
