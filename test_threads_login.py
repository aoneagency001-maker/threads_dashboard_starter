#!/usr/bin/env python3
"""
Тестовый скрипт для проверки авторизации в Threads через threads-api
Использует неофициальную threads-api библиотеку (логин/пароль)
"""

from threads_api.src.threads_api import ThreadsAPI
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_login():
    """Тестирует авторизацию в Threads API"""
    api = ThreadsAPI()

    username = os.getenv('INSTAGRAM_USERNAME')
    password = os.getenv('INSTAGRAM_PASSWORD')

    if not username or not password:
        print("❌ Ошибка: Не найдены INSTAGRAM_USERNAME или INSTAGRAM_PASSWORD в .env файле")
        print("\nДобавьте в .env файл следующие строки:")
        print("INSTAGRAM_USERNAME=ваш_instagram_username")
        print("INSTAGRAM_PASSWORD=ваш_instagram_пароль")
        return False

    print(f"🔐 Попытка входа для пользователя: {username}")
    print("⏳ Авторизация... (это может занять несколько секунд)")

    try:
        # Логин с сохранением токена в .token файл для переиспользования
        is_success = await api.login(
            username=username,
            password=password,
            cached_token_path=".token"
        )

        if is_success:
            print("✅ Успешный вход в Threads API!")
            print("\n📊 Получение информации о профиле...")

            # Тест: получение информации о пользователе
            try:
                user_id = await api.get_user_id_from_username(username)
                print(f"📱 Ваш User ID: {user_id}")

                # Тест: получение профиля
                profile = await api.get_user_profile(user_id)
                print(f"\n👤 Профиль:")
                print(f"   Username: @{profile.username}")
                print(f"   Bio: {profile.biography}")
                print(f"   Подписчиков: {profile.follower_count}")
                print(f"   Подписок: {profile.following_count}")

                print("\n🎉 Все работает отлично! Теперь можно использовать threads-api для публикации постов.")
                print("\n💡 Токен сохранен в файл .token для быстрого переиспользования.")

                await api.close_gracefully()
                return True

            except Exception as e:
                print(f"⚠️ Вход выполнен, но возникла ошибка при получении профиля: {e}")
                await api.close_gracefully()
                return False
        else:
            print("❌ Ошибка входа. Проверьте:")
            print("   1. Правильность username и password в .env файле")
            print("   2. Что Instagram аккаунт не заблокирован")
            print("   3. Что аккаунт подключен к Threads (войдите в приложение Threads хотя бы один раз)")
            print("   4. Если включена двухфакторная аутентификация, попробуйте временно отключить")
            await api.close_gracefully()
            return False

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        await api.close_gracefully()
        return False

async def test_simple_post():
    """Тестирует публикацию простого текстового поста"""
    api = ThreadsAPI()

    username = os.getenv('INSTAGRAM_USERNAME')
    password = os.getenv('INSTAGRAM_PASSWORD')

    if not username or not password:
        print("❌ Не найдены учетные данные в .env")
        return

    print("\n🚀 Тест публикации поста...")

    try:
        # Логин
        is_success = await api.login(
            username=username,
            password=password,
            cached_token_path=".token"
        )

        if is_success:
            print("✅ Авторизация успешна")

            # Создаем тестовый пост
            test_caption = "🤖 Тестовый пост через threads-api библиотеку!"
            print(f"📝 Публикация: '{test_caption}'")

            result = await api.post(caption=test_caption)

            if result and hasattr(result, 'media') and result.media.pk:
                print(f"✅ Пост успешно опубликован!")
                print(f"   Post ID: {result.media.pk}")
                print(f"\n⚠️ ВНИМАНИЕ: Это был реальный пост! Если хотите его удалить, используйте:")
                print(f"   await api.delete_post('{result.media.pk}')")
            else:
                print("❌ Ошибка публикации поста")

        await api.close_gracefully()

    except Exception as e:
        print(f"❌ Ошибка при публикации: {e}")
        await api.close_gracefully()

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ТЕСТ THREADS API (неофициальная threads-api библиотека)")
    print("=" * 60)
    print()

    # Запускаем тест авторизации
    success = asyncio.run(test_login())

    if success:
        print("\n" + "=" * 60)
        response = input("\n❓ Хотите протестировать публикацию реального поста? (да/нет): ").strip().lower()

        if response in ['да', 'yes', 'y', 'д']:
            asyncio.run(test_simple_post())
        else:
            print("✅ Тест завершен. Публикация не выполнена.")

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")
    print("=" * 60)
