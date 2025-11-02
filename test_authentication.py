"""
Тест авторизации для Threads API
Проверяет оба способа: официальный токен и логин/пароль
"""
import os
import asyncio
import requests
from dotenv import load_dotenv
from threads_api.src.threads_api import ThreadsAPI

load_dotenv()

# Официальный токен
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

# Логин/пароль
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")


def test_official_token():
    """Тест официального Instagram Graph API токена"""
    print("\n" + "="*60)
    print("🔐 ТЕСТ 1: Официальный Instagram Graph API токен")
    print("="*60)
    
    if not THREADS_ACCESS_TOKEN:
        print("❌ Токен не найден в .env файле")
        return False
    
    print(f"✅ Токен найден: {THREADS_ACCESS_TOKEN[:50]}...")
    
    # Проверяем токен через Graph API
    try:
        # Получаем информацию о пользователе
        response = requests.get(
            "https://graph.instagram.com/me",
            params={
                "fields": "id,username",
                "access_token": THREADS_ACCESS_TOKEN
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Авторизация успешна!")
            print(f"   User ID: {data.get('id', 'N/A')}")
            print(f"   Username: {data.get('username', 'N/A')}")
            return True
        else:
            print(f"❌ Ошибка авторизации: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение при проверке токена: {e}")
        return False


async def test_login_password():
    """Тест авторизации через логин/пароль (неофициальный API)"""
    print("\n" + "="*60)
    print("🔐 ТЕСТ 2: Авторизация через логин/пароль (threads-api)")
    print("="*60)
    
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        print("❌ Логин или пароль не найдены в .env файле")
        return False
    
    print(f"✅ Учетные данные найдены")
    print(f"   Username: {INSTAGRAM_USERNAME}")
    print(f"   Password: {'*' * len(INSTAGRAM_PASSWORD)}")
    
    api = ThreadsAPI()
    
    try:
        print("\n📡 Попытка авторизации...")
        is_success = await api.login(
            username=INSTAGRAM_USERNAME,
            password=INSTAGRAM_PASSWORD,
            cached_token_path=".token"
        )
        
        if is_success:
            print("✅ Авторизация успешна!")
            print(f"   User ID: {api.user_id}")
            print(f"   Token: {api.token[:50] if api.token else 'N/A'}...")
            print(f"   Logged in: {api.is_logged_in}")
            
            # Тест получения профиля
            try:
                print("\n📡 Тест получения профиля...")
                user_id = await api.get_user_id_from_username(INSTAGRAM_USERNAME)
                if user_id:
                    profile = await api.get_user_profile(user_id)
                    print(f"✅ Профиль получен!")
                    print(f"   Username: {profile.username}")
                    print(f"   Followers: {profile.follower_count}")
                    print(f"   Bio: {profile.biography[:50] if profile.biography else 'N/A'}...")
            except Exception as e:
                print(f"⚠️  Не удалось получить профиль: {e}")
            
            await api.close_gracefully()
            return True
        else:
            print("❌ Авторизация не удалась")
            await api.close_gracefully()
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при авторизации: {e}")
        print(f"   Тип ошибки: {type(e).__name__}")
        try:
            await api.close_gracefully()
        except:
            pass
        return False


async def test_post_creation():
    """Тест создания поста через threads-api"""
    print("\n" + "="*60)
    print("📝 ТЕСТ 3: Создание тестового поста")
    print("="*60)
    
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        print("❌ Логин или пароль не найдены")
        return False
    
    api = ThreadsAPI()
    
    try:
        print("\n📡 Авторизация...")
        is_success = await api.login(
            username=INSTAGRAM_USERNAME,
            password=INSTAGRAM_PASSWORD,
            cached_token_path=".token"
        )
        
        if not is_success:
            print("❌ Авторизация не удалась")
            await api.close_gracefully()
            return False
        
        print("✅ Авторизованы")
        
        # Пробуем создать тестовый пост
        test_caption = "🧪 Тестовый пост из threads_dashboard_starter"
        print(f"\n📝 Создание поста: {test_caption}")
        
        try:
            post_id = await api.post(test_caption)
            if post_id:
                print(f"✅ Пост успешно создан!")
                print(f"   Post ID: {post_id}")
                return True
            else:
                print("❌ Не удалось создать пост")
                return False
        except Exception as e:
            print(f"⚠️  Ошибка при создании поста: {e}")
            print(f"   (Возможно, требуется 2FA или дополнительные разрешения)")
            return False
        finally:
            await api.close_gracefully()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        try:
            await api.close_gracefully()
        except:
            pass
        return False


async def main():
    """Основная функция для запуска всех тестов"""
    print("\n" + "="*60)
    print("🚀 ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ THREADS API")
    print("="*60)
    
    results = {}
    
    # Тест 1: Официальный токен
    results['official_token'] = test_official_token()
    
    # Тест 2: Логин/пароль
    results['login_password'] = await test_login_password()
    
    # Тест 3: Создание поста (только если логин успешен)
    if results['login_password']:
        results['post_creation'] = await test_post_creation()
    
    # Итоговое резюме
    print("\n" + "="*60)
    print("📊 ИТОГОВОЕ РЕЗЮМЕ")
    print("="*60)
    print(f"✅ Официальный токен (Graph API): {'РАБОТАЕТ' if results['official_token'] else 'НЕ РАБОТАЕТ'}")
    print(f"✅ Логин/пароль (threads-api): {'РАБОТАЕТ' if results['login_password'] else 'НЕ РАБОТАЕТ'}")
    if 'post_creation' in results:
        print(f"✅ Создание поста: {'РАБОТАЕТ' if results['post_creation'] else 'НЕ РАБОТАЕТ'}")
    
    print("\n" + "="*60)
    print("💡 РЕКОМЕНДАЦИИ")
    print("="*60)
    
    if results['official_token']:
        print("✅ Используйте официальный токен для продакшена (Graph API)")
        print("   - Более стабильный")
        print("   - Официально поддерживается Meta")
        print("   - Требует настройки Facebook App")
    else:
        print("⚠️  Официальный токен не работает. Проверьте:")
        print("   - Правильность токена")
        print("   - Срок действия токена")
        print("   - Настройки Facebook App")
    
    if results['login_password']:
        print("✅ Логин/пароль работает (неофициальный API)")
        print("   - Можно использовать для разработки")
        print("   - Токен кэшируется в .token файле")
        print("   - ⚠️  Может быть менее стабильным чем официальный API")
    else:
        print("⚠️  Логин/пароль не работает. Возможные причины:")
        print("   - Неправильный логин/пароль")
        print("   - Требуется 2FA")
        print("   - Блокировка со стороны Instagram")
        print("   - Проблемы с библиотекой instagrapi")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())

