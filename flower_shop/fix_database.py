"""
Скрипт для исправления базы данных

Этот скрипт:
1. Выполняет миграции в Django
2. Проверяет и при необходимости добавляет поля telegram_chat_id и telegram_username
3. Выполняет безопасную проверку и очистку проблемных полей

Запуск:
python fix_database.py
"""

import os
import sys
import sqlite3
import django

# Установка переменной окружения для Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_shop.settings')

# Инициализация Django
django.setup()


def run_migrations():
    """Запускает миграции Django"""
    print("Запуск миграций Django...")
    try:
        from django.core.management import call_command
        call_command('migrate')
        print("✅ Миграции успешно выполнены")
    except Exception as e:
        print(f"❌ Ошибка при выполнении миграций: {e}")
        return False
    return True


def check_table_columns(table_name, column_names):
    """
    Проверяет наличие столбцов в таблице SQLite и при необходимости добавляет их

    Args:
        table_name (str): Имя таблицы
        column_names (list): Список имен столбцов для проверки
    """
    import sqlite3
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()

    # Получаем список существующих столбцов
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [column[1] for column in cursor.fetchall()]

    print(f"Существующие столбцы в таблице {table_name}: {existing_columns}")

    # Проверяем и добавляем отсутствующие столбцы
    for col_name in column_names:
        if col_name not in existing_columns:
            print(f"Добавление столбца {col_name} в таблицу {table_name}")
            try:
                # Для telegram_id используем тип INTEGER
                if col_name == 'telegram_id':
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} INTEGER;")
                else:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} TEXT;")
                conn.commit()
                print(f"Столбец {col_name} успешно добавлен")
            except sqlite3.Error as e:
                print(f"Ошибка при добавлении столбца {col_name}: {e}")

    conn.close()


def main():
    """Основная функция запуска всех проверок"""
    print("Начало исправления базы данных...")
    run_migrations()

    # Проверяем и при необходимости добавляем столбцы для telegram
    check_table_columns('users_profile', ['telegram_chat_id', 'telegram_username', 'telegram_id'])

    # Очищаем проблемные профили
    clean_profiles()

    print("Завершено исправление базы данных!")

def clean_profiles():
    """Проверяет и очищает проблемные профили"""
    try:
        from users.models import Profile
        print("Проверка и очистка профилей...")

        # Обновляем все профили с NULL вместо пустых строк
        profiles = Profile.objects.all()
        fixed_count = 0

        for profile in profiles:
            fixed = False

            # Проверяем поля telegram_chat_id и telegram_username
            if hasattr(profile, 'telegram_chat_id') and profile.telegram_chat_id == '':
                profile.telegram_chat_id = None
                fixed = True

            if hasattr(profile, 'telegram_username') and profile.telegram_username == '':
                profile.telegram_username = None
                fixed = True

            if fixed:
                try:
                    profile.save()
                    fixed_count += 1
                except Exception as e:
                    print(f"Ошибка при сохранении профиля {profile.user.username}: {e}")

        print(f"✅ Исправлено профилей: {fixed_count}")
        return True

    except Exception as e:
        print(f"❌ Ошибка при очистке профилей: {e}")
        return False


def main():
    """Основная функция запуска всех проверок"""
    print("=" * 60)
    print("     Утилита исправления базы данных для Floral&Petal     ")
    print("=" * 60)

    # 1. Выполняем миграции Django
    if not run_migrations():
        print("Внимание: миграции не были выполнены должным образом")

    # 2. Проверяем таблицу профилей
    success = check_table_columns(
        'users_profile',
        ['telegram_chat_id', 'telegram_username']
    )

    if not success:
        print("Внимание: проверка структуры таблиц завершилась с ошибками")

    # 3. Очищаем проблемные профили
    if not clean_profiles():
        print("Внимание: очистка профилей завершилась с ошибками")

    print("\n" + "=" * 60)
    print("     Проверка базы данных завершена     ")
    print("=" * 60)
    print("\nЕсли у вас остаются проблемы, обратитесь к администратору.")
    print("Для повторной проверки запустите этот скрипт снова.")


if __name__ == "__main__":
    main()