"""
Тест Threads API через разные endpoints
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_APP_ID = os.getenv("THREADS_APP_ID")

print("="*70)
print("🔐 ДЕТАЛЬНЫЙ ТЕСТ THREADS API")
print("="*70)

# Проверка токена
token = THREADS_ACCESS_TOKEN
print(f"\n📝 Информация о токене:")
print(f"   Длина: {len(token) if token else 0} символов")
print(f"   Первые 50 символов: {token[:50] if token else 'НЕТ'}")
print(f"   Последние 50 символов: {token[-50:] if token else 'НЕТ'}")

# Тест 1: Instagram Graph API /me
print("\n" + "-"*70)
print("ТЕСТ 1: Instagram Graph API - /me")
print("-"*70)

try:
    response = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "id,username,account_type",
            "access_token": token
        },
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Тест 2: Facebook Graph API /me (возможно нужен этот endpoint)
print("\n" + "-"*70)
print("ТЕСТ 2: Facebook Graph API - /me")
print("-"*70)

try:
    response = requests.get(
        "https://graph.facebook.com/v18.0/me",
        params={
            "fields": "id,name",
            "access_token": token
        },
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Тест 3: Threads API напрямую
print("\n" + "-"*70)
print("ТЕСТ 3: Threads API - Прямой запрос")
print("-"*70)

try:
    response = requests.get(
        "https://graph.threads.net/v1.0/me",
        params={
            "access_token": token
        },
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Тест 4: Проверка токена через debug endpoint
print("\n" + "-"*70)
print("ТЕСТ 4: Debug Token")
print("-"*70)

try:
    response = requests.get(
        "https://graph.facebook.com/debug_token",
        params={
            "input_token": token,
            "access_token": token
        },
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Тест 5: Создание поста (без публикации)
print("\n" + "-"*70)
print("ТЕСТ 5: Создание медиа контейнера")
print("-"*70)

if THREADS_USER_ID:
    try:
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{THREADS_USER_ID}/threads",
            data={
                "media_type": "TEXT",
                "text": "Тестовый пост",
                "access_token": token
            },
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

# Тест 6: Альтернативный способ создания поста
print("\n" + "-"*70)
print("ТЕСТ 6: Альтернативный способ (через /media)")
print("-"*70)

if THREADS_USER_ID:
    try:
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{THREADS_USER_ID}/media",
            data={
                "caption": "Тестовый пост",
                "access_token": token
            },
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*70)
print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
print("="*70)

