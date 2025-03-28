from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import TelegramActivationCode, Profile
import random
import string


def register(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт для {username} успешно создан! Теперь вы можете войти в систему.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    """Страница профиля пользователя"""
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    # Генерация кода активации для Telegram, если его еще нет
    telegram_code = None
    telegram_connected = bool(request.user.profile.telegram_chat_id)

    if not telegram_connected:
        # Проверяем, есть ли уже код активации для пользователя
        existing_code = TelegramActivationCode.objects.filter(user=request.user).first()

        if existing_code:
            telegram_code = existing_code.code
        else:
            # Генерируем новый код
            telegram_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            TelegramActivationCode.objects.create(user=request.user, code=telegram_code)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'telegram_code': telegram_code,
        'telegram_connected': telegram_connected,
        'telegram_username': request.user.profile.telegram_username,
    }
    return render(request, 'users/profile.html', context)


@login_required
def telegram_connect(request):
    """Генерация нового кода активации для Telegram"""
    # Удаляем старый код, если есть
    TelegramActivationCode.objects.filter(user=request.user).delete()

    # Генерируем новый код
    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    TelegramActivationCode.objects.create(user=request.user, code=new_code)

    messages.success(request, 'Новый код активации для Telegram успешно сгенерирован!')
    return redirect('profile')