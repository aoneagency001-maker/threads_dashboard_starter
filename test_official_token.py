"""
Тест официального Threads API токена
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_APP_ID = os.getenv("THREADS_APP_ID")
IG_USER_ID = os.getenv("IG_USER_ID") or THREADS_USER_ID

print("="*60)
print("🔐 ТЕСТ ОФИЦИАЛЬНОГО THREADS API ТОКЕНА")
print("="*60)
print(f"\n📝 Настройки:")
print(f"   APP ID: {THREADS_APP_ID}")
print(f"   USER ID: {IG_USER_ID}")
print(f"   TOKEN: {THREADS_ACCESS_TOKEN[:50] if THREADS_ACCESS_TOKEN else 'НЕ НАЙДЕН'}...")

# Тест 1: Проверка токена через Instagram Graph API
print("\n" + "-"*60)
print("📡 ТЕСТ 1: Проверка токена через Instagram Graph API")
print("-"*60)

try:
    response = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "id,username",
            "access_token": THREADS_ACCESS_TOKEN
        }
    )
    
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Авторизация успешна!")
        print(f"   User ID: {data.get('id')}")
        print(f"   Username: {data.get('username', 'N/A')}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(f"   Ответ: {response.text[:300]}")
except Exception as e:
    print(f"❌ Исключение: {e}")

# Тест 2: Проверка через Threads API
print("\n" + "-"*60)
print("📡 ТЕСТ 2: Проверка публикации через Threads API")
print("-"*60)

if not IG_USER_ID:
    print("❌ IG_USER_ID не найден")
else:
    try:
        # Создание медиа контейнера
        test_caption = "🧪 Тестовый пост из threads_dashboard_starter"
        
        create_response = requests.post(
            f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media",
            data={
                "caption": test_caption,
                "access_token": THREADS_ACCESS_TOKEN
            }
        )
        
        print(f"Статус создания контейнера: {create_response.status_code}")
        
        if create_response.status_code == 200:
            create_data = create_response.json()
            if "id" in create_data:
                creation_id = create_data["id"]
                print(f"✅ Контейнер создан: {creation_id}")
                
                # Публикация (закомментировано, чтобы не создавать реальный пост)
                print("\n⚠️  Публикация отключена для теста")
                print(f"   Для публикации раскомментируйте код ниже")
                
                # publish_response = requests.post(
                #     f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media_publish",
                #     data={
                #         "creation_id": creation_id,
                #         "access_token": THREADS_ACCESS_TOKEN
                #     }
                # )
                # 
                # if publish_response.status_code == 200:
                #     publish_data = publish_response.json()
                #     if "id" in publish_data:
                #         print(f"✅ Пост опубликован! ID: {publish_data['id']}")
                #     else:
                #         print(f"❌ Ошибка публикации: {publish_data}")
                # else:
                #     print(f"❌ Ошибка публикации: {publish_response.status_code}")
                #     print(f"   Ответ: {publish_response.text[:300]}")
            else:
                print(f"❌ Ошибка создания контейнера: {create_data}")
        else:
            print(f"❌ Ошибка создания контейнера: {create_response.status_code}")
            print(f"   Ответ: {create_response.text[:300]}")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")

# Тест 3: Проверка информации о пользователе
print("\n" + "-"*60)
print("📡 ТЕСТ 3: Получение информации о пользователе")
print("-"*60)

try:
    response = requests.get(
        f"https://graph.instagram.com/{IG_USER_ID}",
        params={
            "fields": "id,username,account_type",
            "access_token": THREADS_ACCESS_TOKEN
        }
    )
    
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Данные получены:")
        print(f"   ID: {data.get('id')}")
        print(f"   Username: {data.get('username', 'N/A')}")
        print(f"   Account Type: {data.get('account_type', 'N/A')}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(f"   Ответ: {response.text[:300]}")
except Exception as e:
    print(f"❌ Исключение: {e}")

print("\n" + "="*60)
print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("="*60)

