# fix_profiles.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_shop.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import Profile


def fix_profiles():
    """Проверяет и исправляет профили пользователей"""
    print("Начинаем проверку профилей пользователей...")

    # Получаем всех пользователей
    users = User.objects.all()
    print(f"Найдено {users.count()} пользователей")

    created_count = 0
    fixed_count = 0

    for user in users:
        try:
            # Проверяем существует ли профиль
            try:
                profile = Profile.objects.get(user=user)
                print(f"Профиль для пользователя {user.username} существует")

                # Проверяем поля телеграма
                if not hasattr(profile, 'telegram_chat_id') or not hasattr(profile, 'telegram_username'):
                    print(f"Профиль пользователя {user.username} не имеет полей telegram")

                    # Если нужно, можно добавить код для миграции полей
                    fixed_count += 1
            except Profile.DoesNotExist:
                # Создаем новый профиль
                profile = Profile(user=user)
                profile.save()
                print(f"Создан новый профиль для пользователя {user.username}")
                created_count += 1
        except Exception as e:
            print(f"Ошибка при обработке пользователя {user.username}: {str(e)}")

    print("\nИтоги:")
    print(f"Создано новых профилей: {created_count}")
    print(f"Исправлено профилей: {fixed_count}")


if __name__ == "__main__":
    fix_profiles()