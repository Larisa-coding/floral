from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from datetime import timedelta
from django import forms
from products.models import Product
from .models import Cart, CartItem, Order, OrderItem


def create_or_get_cart(user):
    """Вспомогательная функция для создания или получения корзины пользователя"""
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart(request):
    """Отображение корзины покупок"""
    cart = create_or_get_cart(request.user)
    cart_items = cart.cart_items.all()

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': cart.subtotal(),
        'shipping_cost': cart.shipping_cost(),
        'total': cart.total(),
    }
    return render(request, 'orders/cart.html', context)


@login_required
def add_to_cart(request, product_id):
    """Добавление товара в корзину"""
    product = get_object_or_404(Product, id=product_id, available=True)
    cart = create_or_get_cart(request.user)

    # Проверяем, есть ли уже этот товар в корзине
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )

    # Если товар уже был в корзине, увеличиваем количество
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f'"{product.name}" добавлен в корзину!')

    # Возвращаемся на страницу, с которой пришел запрос
    next_url = request.GET.get('next', 'product_list')
    return redirect(next_url)


@login_required
def update_cart(request, item_id):
    """Обновление количества товара в корзине"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))

        if quantity > 0 and quantity <= cart_item.product.stock:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Корзина обновлена!')
        else:
            messages.error(request, f'Пожалуйста, выберите количество от 1 до {cart_item.product.stock}.')

    return redirect('cart')


@login_required
def remove_from_cart(request, item_id):
    """Удаление товара из корзины"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()

    messages.success(request, f'"{product_name}" удален из корзины!')
    return redirect('cart')


@login_required
def clear_cart(request):
    """Очистка всех товаров из корзины"""
    cart = create_or_get_cart(request.user)
    cart.cart_items.all().delete()

    messages.success(request, 'Корзина очищена!')
    return redirect('cart')


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'postal_code', 'country']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


@login_required
def checkout(request):
    """Страница оформления заказа"""
    cart = create_or_get_cart(request.user)
    cart_items = cart.cart_items.all()

    # Проверяем, не пуста ли корзина
    if not cart_items:
        messages.error(request, 'Ваша корзина пуста. Добавьте товары перед оформлением заказа.')
        return redirect('product_list')

    # Предзаполняем форму данными пользователя
    try:
        # Попытка получить данные профиля пользователя
        profile = getattr(request.user, 'profile', None)

        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }

        # Добавляем данные из профиля, если профиль существует
        if profile:
            initial_data.update({
                'phone': getattr(profile, 'phone', ''),
                'address': getattr(profile, 'address', ''),
                'city': getattr(profile, 'city', ''),
                'postal_code': getattr(profile, 'postal_code', ''),
                'country': getattr(profile, 'country', '') or 'Россия',
            })
    except Exception as e:
        # В случае ошибки используем только основные данные пользователя
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }

    form = OrderForm(initial=initial_data)

    context = {
        'form': form,
        'cart': cart,
        'cart_items': cart_items,
        'shipping_cost': cart.shipping_cost(),
        'total': cart.total(),
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def place_order(request):
    """Обработка заказа"""
    cart = create_or_get_cart(request.user)
    cart_items = cart.cart_items.all()

    # Проверяем, не пуста ли корзина
    if not cart_items:
        messages.error(request, 'Ваша корзина пуста. Добавьте товары перед оформлением заказа.')
        return redirect('product_list')

    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            # Создаем заказ
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = cart.subtotal()
            order.shipping_cost = cart.shipping_cost()
            order.total = cart.total()
            order.save()

            # Добавляем товары из корзины в заказ
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    price=cart_item.product.price,
                    quantity=cart_item.quantity
                )

                # Обновляем остаток товара
                product = cart_item.product
                product.stock -= cart_item.quantity
                if product.stock <= 0:
                    product.available = False
                product.save()

            # Очищаем корзину
            cart_items.delete()

            # Отправляем уведомление через Telegram, обрабатываем ошибки чтобы не блокировать процесс
            try:
                from telegram_bot.bot import send_order_notification
                send_order_notification(order.id)
            except (ImportError, Exception) as e:
                # Логируем ошибку, но продолжаем обработку
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Не удалось отправить уведомление о заказе в Telegram: {e}")

            messages.success(request, 'Ваш заказ успешно оформлен!')
            return redirect('order_success', order_id=order.id)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = OrderForm()

    context = {
        'form': form,
        'cart': cart,
        'cart_items': cart_items,
        'shipping_cost': cart.shipping_cost(),
        'total': cart.total(),
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_success(request, order_id):
    """Страница успешного оформления заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        'order': order,
    }
    return render(request, 'orders/order_success.html', context)


@login_required
def order_list(request):
    """Отображение заказов пользователя"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Фильтры
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')

    if status:
        orders = orders.filter(status=status)

    if date_from:
        orders = orders.filter(created_at__gte=date_from)

    # Пагинация
    paginator = Paginator(orders, 5)  # 5 заказов на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
        'status': status,
        'date_from': date_from,
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, order_id):
    """Отображение деталей заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        'order': order,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def cancel_order(request, order_id):
    """Отмена заказа пользователем"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Проверяем, можно ли отменить заказ (только если он в статусе "в ожидании")
    if order.status != 'pending':
        messages.error(request, 'Заказ не может быть отменен, так как он уже находится в обработке.')
        return redirect('order_list')

    if request.method == 'POST':
        # Возвращаем товары в наличие
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.available = True
            product.save()

        # Меняем статус заказа на "отменен"
        order.status = 'cancelled'
        order.save()

        # Пробуем отправить уведомление через Telegram
        try:
            from telegram_bot.bot import send_status_update_notification
            send_status_update_notification(order.id)
        except Exception as e:
            # Логируем ошибку, но продолжаем обработку
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Не удалось отправить уведомление об отмене заказа в Telegram: {e}")

        messages.success(request, f'Заказ №{order.order_number} успешно отменен.')

    return redirect('order_list')


# Административные функции

@login_required
def admin_dashboard(request):
    """Панель администратора"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    # Общая статистика
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(Sum('total'))['total__sum'] or 0
    total_products = Product.objects.count()
    total_users = User.objects.count()

    # Статистика по статусам заказов
    orders_by_status = Order.objects.values('status').annotate(count=Count('status'))
    status_counts = {status: 0 for status, _ in Order.STATUS_CHOICES}

    for status_data in orders_by_status:
        status_counts[status_data['status']] = status_data['count']

    # Расчет процентов для визуализации
    pending_count = status_counts['pending']
    processing_count = status_counts['processing']
    shipped_count = status_counts['shipped']
    delivered_count = status_counts['delivered']
    cancelled_count = status_counts['cancelled']

    total_count = total_orders or 1  # Избегаем деления на ноль

    # Последние заказы
    recent_orders = Order.objects.all().order_by('-created_at')[:5]

    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'total_users': total_users,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'shipped_count': shipped_count,
        'delivered_count': delivered_count,
        'cancelled_count': cancelled_count,
        'pending_percent': round(pending_count / total_count * 100),
        'processing_percent': round(processing_count / total_count * 100),
        'shipped_percent': round(shipped_count / total_count * 100),
        'delivered_percent': round(delivered_count / total_count * 100),
        'cancelled_percent': round(cancelled_count / total_count * 100),
        'recent_orders': recent_orders,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
def admin_orders(request):
    """Управление заказами администратором"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    orders = Order.objects.all().order_by('-created_at')

    # Фильтры
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')

    if status:
        orders = orders.filter(status=status)

    if date_from:
        orders = orders.filter(created_at__gte=date_from)

    if date_to:
        # Добавляем день, чтобы включить весь указанный день
        end_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date() + timedelta(days=1)
        orders = orders.filter(created_at__lt=end_date)

    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    # Пагинация
    paginator = Paginator(orders, 10)  # 10 заказов на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj,
    }
    return render(request, 'admin/orders.html', context)


@login_required
def admin_order_detail(request, order_id):
    """Детали заказа для администратора"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    order = get_object_or_404(Order, id=order_id)

    # Получаем профиль пользователя с информацией о телеграме
    user_profile = None
    telegram_connected = False
    telegram_id = None
    telegram_username = None

    try:
        user_profile = order.user.profile
        # Проверяем наличие telegram полей в профиле
        if hasattr(user_profile, 'telegram_chat_id') and user_profile.telegram_chat_id:
            telegram_connected = True
            telegram_id = user_profile.telegram_chat_id
        elif hasattr(user_profile, 'telegram_id') and user_profile.telegram_id:
            telegram_connected = True
            telegram_id = user_profile.telegram_id

        if hasattr(user_profile, 'telegram_username') and user_profile.telegram_username:
            telegram_username = user_profile.telegram_username
    except (AttributeError, Profile.DoesNotExist):
        # Если профиль не существует или возникла ошибка
        pass

    context = {
        'order': order,
        'telegram_connected': telegram_connected,
        'telegram_id': telegram_id,
        'telegram_username': telegram_username
    }
    return render(request, 'admin/order_detail.html', context)


@login_required
def update_order_status(request, order_id):
    """Обновление статуса заказа"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    order = get_object_or_404(Order, id=order_id)
    previous_status = order.status

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()

            # Отправляем уведомление через Telegram
            try:
                from telegram_bot.bot import send_status_update_notification
                send_status_update_notification(order.id)
            except (ImportError, Exception) as e:
                # Логируем ошибку, но продолжаем обработку
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Не удалось отправить уведомление о смене статуса заказа в Telegram: {e}")

            messages.success(request, f'Статус заказа #{order.order_number} изменен на "{order.get_status_display()}"')
        else:
            messages.error(request, 'Некорректный статус заказа')

    return redirect('admin_order_detail', order_id=order.id)


@login_required
def send_telegram_notification(request, order_id):
    """Отправка пользовательского уведомления в Telegram клиенту"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        message = request.POST.get('message', '')

        if message:
            try:
                from telegram_bot.bot import send_custom_notification
                if send_custom_notification(order.id, message):
                    messages.success(request, 'Уведомление успешно отправлено')
                else:
                    messages.error(request,
                                   'Не удалось отправить уведомление. Пожалуйста, проверьте настройки Telegram.')
            except (ImportError, Exception) as e:
                # Логируем ошибку и показываем сообщение
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Не удалось отправить произвольное уведомление в Telegram: {e}")
                messages.error(request, f'Ошибка при отправке уведомления: {str(e)}')
        else:
            messages.error(request, 'Пожалуйста, введите текст сообщения')

    return redirect('admin_order_detail', order_id=order.id)


@login_required
def admin_products(request):
    """Управление товарами администратором"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    products = Product.objects.all().order_by('-created_at')

    # Фильтры
    category = request.GET.get('category')
    available = request.GET.get('available')
    featured = request.GET.get('featured')
    search = request.GET.get('search')

    if category:
        products = products.filter(category__id=category)

    if available:
        is_available = available == 'true'
        products = products.filter(available=is_available)

    if featured:
        is_featured = featured == 'true'
        products = products.filter(featured=is_featured)

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    # Пагинация
    paginator = Paginator(products, 12)  # 12 товаров на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
    }
    return render(request, 'admin/products.html', context)


@login_required
def admin_users(request):
    """Управление пользователями администратором"""
    if not request.user.is_staff:
        return HttpResponseForbidden()

    users = User.objects.all().order_by('-date_joined')

    # Фильтры
    is_staff = request.GET.get('is_staff')
    is_active = request.GET.get('is_active')
    search = request.GET.get('search')

    if is_staff:
        is_staff_bool = is_staff == 'true'
        users = users.filter(is_staff=is_staff_bool)

    if is_active:
        is_active_bool = is_active == 'true'
        users = users.filter(is_active=is_active_bool)

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    # Статистика
    total_users = users.count()
    staff_users = users.filter(is_staff=True).count()
    active_users = users.filter(is_active=True).count()
    inactive_users = users.filter(is_active=False).count()

    # Пагинация
    paginator = Paginator(users, 20)  # 20 пользователей на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'total_users': total_users,
        'staff_users': staff_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
    }
    return render(request, 'admin/users.html', context)