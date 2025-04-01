from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import Profile


class UserRegisterForm(UserCreationForm):
    """Форма регистрации нового пользователя"""
    first_name = forms.CharField(label='Имя', max_length=100, required=True,
                                 help_text='Введите ваше имя')
    last_name = forms.CharField(label='Фамилия', max_length=100, required=True,
                                help_text='Введите вашу фамилию')
    email = forms.EmailField(label='Email', required=True,
                             help_text='Введите действующий email адрес')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        labels = {
            'username': 'Имя пользователя',
        }
        help_texts = {
            'username': 'Введите уникальное имя пользователя. Максимум 150 символов. Только буквы, цифры и символы @/./+/-/_.',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Проверка уникальности email
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Этот email уже используется. Пожалуйста, используйте другой.')
        return email


class UserUpdateForm(forms.ModelForm):
    """Форма обновления данных пользователя"""
    email = forms.EmailField(label='Email')
    first_name = forms.CharField(label='Имя', max_length=100)
    last_name = forms.CharField(label='Фамилия', max_length=100)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Проверяем, не занят ли email другим пользователем
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('Этот email уже используется. Пожалуйста, используйте другой.')
        return email


class ProfileUpdateForm(forms.ModelForm):
    """Форма обновления профиля пользователя"""
    phone = forms.CharField(label='Телефон', max_length=20, required=False,
                            help_text='Введите контактный телефон')
    address = forms.CharField(label='Адрес', widget=forms.Textarea(attrs={'rows': 3}), required=False)
    city = forms.CharField(label='Город', required=False)
    postal_code = forms.CharField(label='Почтовый индекс', required=False)
    country = forms.CharField(label='Страна', initial='Россия', required=False)

    class Meta:
        model = Profile
        fields = ['phone', 'address', 'city', 'postal_code', 'country']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Безопасная инициализация формы даже при отсутствии полей в базе
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Проверка наличия полей в модели
            for field in self.fields:
                if not hasattr(self.instance.__class__, field):
                    logger.warning(f"В модели Profile отсутствует поле {field}")
                    # Удаляем поле из формы, если его нет в модели
                    self.fields.pop(field, None)
        except Exception as e:
            logger.error(f"Ошибка при проверке полей модели Profile: {e}")


class ShippingAddressForm(forms.ModelForm):
    """Форма для адреса доставки при оформлении заказа"""
    address = forms.CharField(label='Адрес', widget=forms.Textarea(attrs={'rows': 3}), required=True)
    city = forms.CharField(label='Город', required=True)
    postal_code = forms.CharField(label='Почтовый индекс', required=True)
    country = forms.CharField(label='Страна', initial='Россия', required=True)

    class Meta:
        model = Profile
        fields = ['address', 'city', 'postal_code', 'country']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Безопасная инициализация формы
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Проверка обязательных полей
            for field in self.fields:
                if not hasattr(self.instance.__class__, field):
                    logger.warning(f"В модели Profile отсутствует поле {field}")
                else:
                    # Делаем все поля обязательными для заполнения
                    self.fields[field].required = True
        except Exception as e:
            logger.error(f"Ошибка при инициализации формы ShippingAddressForm: {e}")


class CustomPasswordChangeForm(PasswordChangeForm):
    """Кастомная форма для смены пароля с русифицированными сообщениями"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Текущий пароль'
        self.fields['new_password1'].label = 'Новый пароль'
        self.fields['new_password2'].label = 'Подтверждение нового пароля'
        self.fields['old_password'].help_text = 'Введите ваш текущий пароль для подтверждения'
        self.fields[
            'new_password1'].help_text = 'Пароль должен содержать не менее 8 символов и не должен быть слишком простым'
        self.fields['new_password2'].help_text = 'Введите новый пароль повторно для подтверждения'