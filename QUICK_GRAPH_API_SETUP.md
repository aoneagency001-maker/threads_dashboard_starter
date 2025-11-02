# Быстрая настройка Instagram Graph API для Threads

Этот метод работает с 2FA и более надежен чем неофициальное API.

## Шаг 1: Убедитесь, что у вас Business аккаунт

1. Откройте Instagram приложение
2. Перейдите в Настройки → Тип аккаунта
3. Если у вас Personal аккаунт, переключите на Business или Creator

## Шаг 2: Создайте Facebook Page (если нет)

1. Зайдите на https://www.facebook.com/pages/create
2. Создайте страницу для вашего бизнеса
3. Привяжите Instagram аккаунт к этой странице:
   - Instagram → Настройки → Бизнес → Связанные аккаунты → Facebook
   - Выберите вашу страницу

## Шаг 3: Создайте Facebook App

1. Перейдите на https://developers.facebook.com/apps
2. Нажмите "Create App"
3. Выберите "Business" или "Other"
4. Заполните:
   - App name: "Threads Quote Publisher" (или любое название)
   - App contact email: ваш email
5. Нажмите "Create App"

## Шаг 4: Добавьте Instagram Graph API

1. В панели вашего приложения найдите "Add Products"
2. Найдите "Instagram Graph API" или "Instagram Basic Display"
3. Нажмите "Set Up"

## Шаг 5: Получите краткосрочный Access Token

### Способ A: Через Graph API Explorer (проще)

1. Откройте https://developers.facebook.com/tools/explorer/
2. Выберите ваше приложение в выпадающем меню
3. Нажмите "Generate Access Token"
4. Выберите разрешения:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
5. Нажмите "Generate Token"
6. **Скопируйте токен** - это ваш `THREADS_ACCESS_TOKEN`

### Способ B: Через Facebook Login Flow

1. В вашем приложении перейдите в Facebook Login → Settings
2. Добавьте Valid OAuth Redirect URIs: `https://localhost`
3. Используйте этот URL (замените YOUR_APP_ID):
   ```
   https://www.facebook.com/v18.0/dialog/oauth?client_id=YOUR_APP_ID&redirect_uri=https://localhost&scope=instagram_basic,instagram_content_publish,pages_read_engagement
   ```
4. Откройте URL в браузере, разрешите доступ
5. Скопируйте `code` из адресной строки
6. Обменяйте код на токен (см. документацию)

## Шаг 6: Получите Instagram Business Account ID

1. Откройте Graph API Explorer: https://developers.facebook.com/tools/explorer/
2. Вставьте ваш токен
3. Выполните запрос: `GET /me/accounts`
4. Найдите вашу страницу в ответе
5. Выполните запрос: `GET /{page-id}?fields=instagram_business_account`
6. Скопируйте значение `instagram_business_account.id` - это ваш `IG_USER_ID`

## Шаг 7: Добавьте в .env файл

```env
# Официальный Instagram Graph API
THREADS_ACCESS_TOKEN=ваш_токен_из_шага_5
IG_USER_ID=ваш_user_id_из_шага_6
```

## Шаг 8: Протестируйте

Создайте файл `test_graph_api.py`:

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

# Тест 1: Проверка токена
response = requests.get(
    f"https://graph.facebook.com/v18.0/{IG_USER_ID}",
    params={"access_token": ACCESS_TOKEN, "fields": "id,username"}
)
print("Проверка токена:", response.json())

# Тест 2: Создание тестового поста
test_caption = "Тестовый пост через Graph API"
create_response = requests.post(
    f"https://graph.facebook.com/v18.0/{IG_USER_ID}/threads",
    data={
        "media_type": "TEXT",
        "text": test_caption,
        "access_token": ACCESS_TOKEN
    }
)
print("Создание контейнера:", create_response.json())

if "id" in create_response.json():
    creation_id = create_response.json()["id"]

    # Публикация
    publish_response = requests.post(
        f"https://graph.facebook.com/v18.0/{IG_USER_ID}/threads_publish",
        data={
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN
        }
    )
    print("Публикация:", publish_response.json())
```

Запустите:
```bash
python3 test_graph_api.py
```

## Шаг 9: Запустите приложение

```bash
streamlit run app.py
```

Приложение автоматически определит, что настроен Graph API, и будет использовать его для публикации.

---

## Решение проблем

### "Токен истек"

Краткосрочные токены живут 1-2 часа. Для продакшена нужен долгосрочный токен.

**Получение долгосрочного токена:**

```bash
curl -i -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

Долгосрочный токен живет ~60 дней.

### "User ID не найден"

Убедитесь, что:
1. Instagram аккаунт переключен на Business/Creator
2. Instagram привязан к Facebook странице
3. Вы используете правильный `instagram_business_account.id`

### "Недостаточно разрешений"

В Graph API Explorer добавьте разрешения:
- `instagram_basic`
- `instagram_content_publish`
- `pages_read_engagement`

---

## Преимущества официального API

✅ Работает с 2FA
✅ Стабильнее неофициального
✅ Не блокируется Instagram
✅ Официально поддерживается Meta
✅ Долгосрочные токены

## Недостатки

❌ Требует больше настройки
❌ Нужен Business аккаунт
❌ Нужна Facebook страница
❌ Токены нужно обновлять каждые 60 дней

---

## Полезные ссылки

- Facebook Developers: https://developers.facebook.com/
- Graph API Explorer: https://developers.facebook.com/tools/explorer/
- Instagram API Docs: https://developers.facebook.com/docs/instagram-api/
- Threads API Docs: https://developers.facebook.com/docs/threads/

---

Готово! После настройки ваше приложение будет работать стабильно с 2FA.
