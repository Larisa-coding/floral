from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, ShippingAddressForm
from .models import TelegramActivationCode, Profile
import random
import string
import logging


def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан! Теперь вы можете войти.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    """Просмотр профиля пользователя"""
    try:
        # Подготовим контекст с проверкой на ошибки
        from django.db import OperationalError
        logger = logging.getLogger(__name__)

        # Получаем профиль пользователя безопасным способом
        try:
            profile = request.user.profile
            # Проверка существования полей telegram в модели Profile
            context = {}
            # Проверка наличия полей
            has_telegram_chat_id = hasattr(profile, 'telegram_chat_id')
            has_telegram_username = hasattr(profile, 'telegram_username')

            if not has_telegram_chat_id or not has_telegram_username:
                logger.warning(f"Profile for user {request.user.username} is missing telegram fields")
                context['profile_error'] = True
                context['missing_telegram_fields'] = True
                # Уведомляем пользователя о необходимости запустить скрипт fix_database.py
                messages.warning(request,
                                 "Обнаружены проблемы с вашим профилем. Пожалуйста, обратитесь к администратору.")
                return render(request, 'users/profile.html', context)

            # Получаем код активации Telegram, если есть
            try:
                activation_code = TelegramActivationCode.objects.filter(user=request.user).first()
                if activation_code:
                    context['telegram_code'] = activation_code.code
            except Exception as e:
                logger.error(f"Error getting activation code: {str(e)}")

            # Добавляем информацию о подключенном Telegram
            if profile.telegram_chat_id:
                context['telegram_connected'] = True
                context['telegram_username'] = profile.telegram_username

            return render(request, 'users/profile.html', context)
        except (AttributeError, OperationalError) as e:
            # Ошибка с профилем или полями
            logger.error(f"Error accessing profile fields: {str(e)}")

            # Создаем минимальный контекст
            context = {'profile_error': True}
            return render(request, 'users/profile.html', context)
    except Exception as e:
        # Если возникла другая ошибка, логируем её и выдаем пользователю сообщение
        logger = logging.getLogger(__name__)
        logger.error(f"Error in profile view: {str(e)}")
        messages.error(request, "Произошла ошибка при загрузке профиля. Администраторы уведомлены.")
        return redirect('home')


@login_required
def update_profile(request):
    """Обновление профиля пользователя"""
    try:
        from django.db import OperationalError

        # Безопасно получаем профиль пользователя
        try:
            profile = request.user.profile
        except (AttributeError, OperationalError) as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error accessing profile in update_profile: {str(e)}")
            messages.error(request, "Произошла ошибка при доступе к профилю. Администраторы уведомлены.")
            return redirect('home')

        if request.method == 'POST':
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileUpdateForm(request.POST, instance=profile)

            if u_form.is_valid() and p_form.is_valid():
                try:
                    u_form.save()
                    p_form.save()
                    messages.success(request, 'Ваш профиль успешно обновлен!')
                    return redirect('profile')
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error saving profile update: {str(e)}")
                    messages.error(request, "Произошла ошибка при сохранении профиля. Попробуйте еще раз.")
        else:
            u_form = UserUpdateForm(instance=request.user)
            p_form = ProfileUpdateForm(instance=profile)

        context = {
            'u_form': u_form,
            'p_form': p_form,
        }
        return render(request, 'users/update_profile.html', context)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in update_profile: {str(e)}")
        messages.error(request, "Произошла неожиданная ошибка. Администраторы уведомлены.")
        return redirect('home')


@login_required
def update_shipping(request):
    """Обновление адреса доставки"""
    try:
        from django.db import OperationalError

        # Безопасно получаем профиль пользователя
        try:
            profile = request.user.profile
        except (AttributeError, OperationalError) as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error accessing profile in update_shipping: {str(e)}")
            messages.error(request, "Произошла ошибка при доступе к профилю. Администраторы уведомлены.")
            return redirect('home')

        if request.method == 'POST':
            form = ShippingAddressForm(request.POST, instance=profile)

            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, 'Ваш адрес доставки успешно обновлен!')
                    return redirect('profile')
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error saving shipping address: {str(e)}")
                    messages.error(request, "Произошла ошибка при сохранении адреса. Попробуйте еще раз.")
        else:
            form = ShippingAddressForm(instance=profile)

        context = {
            'form': form,
        }
        return render(request, 'users/update_shipping.html', context)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in update_shipping: {str(e)}")
        messages.error(request, "Произошла неожиданная ошибка. Администраторы уведомлены.")
        return redirect('home')


@login_required
def change_password(request):
    """Изменение пароля пользователя"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Обновляем сессию, чтобы пользователь не вылетел после смены пароля
            update_session_auth_hash(request, user)
            messages.success(request, 'Ваш пароль был успешно изменен!')
            return redirect('profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/change_password.html', {'form': form})


def generate_activation_code(length=8):
    """Генерирует случайный код активации"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@login_required
def connect_telegram(request):
    """Подключение Telegram аккаунта"""
    try:
        # Удаляем старые коды активации пользователя, если они есть
        try:
            TelegramActivationCode.objects.filter(user=request.user).delete()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Error deleting old activation codes: {str(e)}")
            # Продолжаем выполнение, так как это не критическая ошибка

        # Создаем новый код активации
        code = generate_activation_code()
        try:
            TelegramActivationCode.objects.create(user=request.user, code=code)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating activation code: {str(e)}")
            messages.error(request, "Ошибка при создании кода активации. Попробуйте позже.")
            return redirect('profile')

        context = {
            'activation_code': code,
        }
        return render(request, 'users/connect_telegram.html', context)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in connect_telegram: {str(e)}")
        messages.error(request, "Произошла неожиданная ошибка. Администраторы уведомлены.")
        return redirect('home')


@login_required
def disconnect_telegram(request):
    """Отключение Telegram аккаунта"""
    try:
        if request.method == 'POST':
            try:
                profile = request.user.profile
                profile.telegram_chat_id = None
                profile.telegram_username = None
                profile.save()

                messages.success(request, 'Ваш Telegram аккаунт успешно отключен!')
                return redirect('profile')
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error disconnecting Telegram: {str(e)}")
                messages.error(request, "Произошла ошибка при отключении Telegram. Администраторы уведомлены.")
                return redirect('profile')

        return render(request, 'users/disconnect_telegram.html')
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in disconnect_telegram: {str(e)}")
        messages.error(request, "Произошла неожиданная ошибка. Администраторы уведомлены.")
        return redirect('home')