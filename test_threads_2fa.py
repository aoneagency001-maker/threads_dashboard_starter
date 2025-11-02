#!/usr/bin/env python3
"""
Тестовый скрипт для авторизации в Threads с поддержкой 2FA
"""

from threads_api.src.threads_api import ThreadsAPI
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_login_with_2fa():
    """Тестирует авторизацию в Threads API с 2FA"""
    api = ThreadsAPI()

    username = os.getenv('INSTAGRAM_USERNAME')
    password = os.getenv('INSTAGRAM_PASSWORD')

    if not username or not password:
        print("❌ Ошибка: Не найдены INSTAGRAM_USERNAME или INSTAGRAM_PASSWORD в .env файле")
        return False

    print(f"🔐 Попытка входа для пользователя: {username}")
    print("⏳ Авторизация...")

    try:
        # Попытка логина
        is_success = await api.login(
            username=username,
            password=password,
            cached_token_path=".token"
        )

        if is_success:
            print("✅ Успешный вход в Threads API!")

            # Получаем информацию о профиле
            user_id = await api.get_user_id_from_username(username)
            print(f"📱 Ваш User ID: {user_id}")

            profile = await api.get_user_profile(user_id)
            print(f"\n👤 Профиль:")
            print(f"   Username: @{profile.username}")
            print(f"   Bio: {profile.biography}")
            print(f"   Подписчиков: {profile.follower_count}")

            print("\n🎉 Все работает отлично!")
            await api.close_gracefully()
            return True
        else:
            print("❌ Ошибка входа")
            print("\n📧 ВАЖНО: У вас включена 2FA!")
            print("\nВарианты решения:")
            print("1. Отключите 2FA в настройках Instagram")
            print("2. Или используйте код приложения аутентификации")
            print("3. Или используйте официальный Graph API")

            await api.close_gracefully()
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Ошибка: {error_msg}")

        if "two_factor_required" in error_msg.lower() or "checkpoint" in error_msg.lower():
            print("\n📧 Обнаружена двухфакторная аутентификация!")
            print("\nДля работы с 2FA нужно:")
            print("1. Временно отключить 2FA в Instagram")
            print("2. Авторизоваться и получить токен")
            print("3. После этого можно снова включить 2FA")

        await api.close_gracefully()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ТЕСТ АВТОРИЗАЦИИ THREADS С ПРОВЕРКОЙ 2FA")
    print("=" * 60)
    print()

    asyncio.run(test_login_with_2fa())

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")
    print("=" * 60)
