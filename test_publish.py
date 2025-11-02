"""
Тест публикации поста через Threads API
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")

print("="*70)
print("📝 ТЕСТ ПУБЛИКАЦИИ ПОСТА В THREADS")
print("="*70)

if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
    print("❌ Токен или USER_ID не найден")
    exit(1)

test_caption = "🧪 Тестовый пост из threads_dashboard_starter - проверка работы API"

print(f"\n📝 Текст поста: {test_caption}")
print(f"👤 User ID: {THREADS_USER_ID}")

# Метод 1: Прямой запрос через Threads API
print("\n" + "-"*70)
print("МЕТОД 1: Прямой запрос через graph.threads.net")
print("-"*70)

try:
    response = requests.post(
        f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads",
        data={
            "media_type": "TEXT",
            "text": test_caption,
            "access_token": THREADS_ACCESS_TOKEN
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if "id" in data:
            print(f"✅ Пост успешно создан! Post ID: {data['id']}")
        else:
            print(f"⚠️ Ответ получен, но ID поста не найден: {data}")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        
except Exception as e:
    print(f"❌ Исключение: {e}")

# Метод 2: Через Instagram Graph API (старый метод)
print("\n" + "-"*70)
print("МЕТОД 2: Через Instagram Graph API (для сравнения)")
print("-"*70)

try:
    # Создание контейнера
    create_response = requests.post(
        f"https://graph.facebook.com/v18.0/{THREADS_USER_ID}/media",
        data={
            "caption": test_caption,
            "access_token": THREADS_ACCESS_TOKEN
        },
        timeout=30
    )
    
    print(f"Create Status: {create_response.status_code}")
    print(f"Create Response: {create_response.text[:300]}")
    
    if create_response.status_code == 200:
        create_data = create_response.json()
        if "id" in create_data:
            creation_id = create_data["id"]
            print(f"✅ Контейнер создан: {creation_id}")
            
            # Публикация
            publish_response = requests.post(
                f"https://graph.facebook.com/v18.0/{THREADS_USER_ID}/media_publish",
                data={
                    "creation_id": creation_id,
                    "access_token": THREADS_ACCESS_TOKEN
                },
                timeout=30
            )
            
            print(f"Publish Status: {publish_response.status_code}")
            print(f"Publish Response: {publish_response.text[:300]}")
            
            if publish_response.status_code == 200:
                publish_data = publish_response.json()
                if "id" in publish_data:
                    print(f"✅ Пост опубликован! Post ID: {publish_data['id']}")
                else:
                    print(f"⚠️ Ответ получен, но ID не найден: {publish_data}")
            else:
                print(f"❌ Ошибка публикации")
        else:
            print(f"❌ Ошибка создания контейнера: {create_data}")
    else:
        print(f"❌ Ошибка создания контейнера")
        
except Exception as e:
    print(f"❌ Исключение: {e}")

print("\n" + "="*70)
print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("="*70)

