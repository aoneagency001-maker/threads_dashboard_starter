# 🔑 Как обновить токен Threads API

## Проблема
Ваш токен истёк: `Session has expired on Saturday, 01-Nov-25`

## Решение

### Вариант 1: Обновить токен через Meta Developer Console

1. **Перейдите на https://developers.facebook.com/**

2. **Выберите ваше приложение Threads**

3. **Graph API Explorer:**
   - Перейдите в Tools → Graph API Explorer
   - Выберите ваше приложение
   - Запросите новый Access Token с правами:
     - `threads_basic`
     - `threads_content_publish`
     - `threads_manage_insights`

4. **Скопируйте новый токен**

5. **Обновите `.env` файл:**
   ```env
   THREADS_ACCESS_TOKEN=ваш_новый_токен_здесь
   ```

6. **Перезапустите приложение:**
   ```bash
   # Остановите текущий процесс (Ctrl+C)
   streamlit run app_gemini.py
   ```

### Вариант 2: Долгосрочный токен (60 дней)

**Обменяйте краткосрочный токен на долгосрочный:**

```bash
curl -i -X GET "https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret={app-secret}&access_token={short-lived-access-token}"
```

Параметры:
- `{app-secret}` - секрет вашего приложения из Meta Developer Console
- `{short-lived-access-token}` - ваш текущий токен

Ответ:
```json
{
  "access_token": "новый_долгосрочный_токен",
  "token_type": "bearer",
  "expires_in": 5184000
}
```

Обновите `.env`:
```env
THREADS_ACCESS_TOKEN=новый_долгосрочный_токен
```

### Вариант 3: Публикация вручную (временное решение)

Пока не обновите токен, можете публиковать вручную:

1. **В приложении нажмите "📋 Копировать текст"**
2. **Скопируйте текст инсайта**
3. **Откройте приложение Threads на телефоне**
4. **Вставьте текст и опубликуйте**

## Проверка токена

После обновления проверьте токен:

```bash
curl -i -X GET "https://graph.threads.net/v1.0/me?fields=id,username,threads_profile_picture_url&access_token={access-token}"
```

Если токен валидный, вы увидите ваш профиль.

## Автоматическое обновление (в будущем)

Можно настроить автоматическое обновление токена перед истечением срока. Добавьте в код:

```python
import requests
from datetime import datetime, timedelta

def refresh_token_if_needed(current_token, app_secret):
    """Обновляет токен если срок истекает через 7 дней"""
    # Проверяем срок действия
    response = requests.get(
        f"https://graph.threads.net/debug_token?input_token={current_token}&access_token={current_token}"
    )

    data = response.json()
    expires_at = data.get("data", {}).get("expires_at", 0)

    if expires_at == 0:
        return current_token  # Токен не истекает

    # Если осталось меньше 7 дней - обновляем
    if datetime.fromtimestamp(expires_at) - datetime.now() < timedelta(days=7):
        refresh_response = requests.get(
            f"https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret={app_secret}&access_token={current_token}"
        )

        new_data = refresh_response.json()
        return new_data.get("access_token", current_token)

    return current_token
```

## Дополнительные ссылки

- [Threads API Documentation](https://developers.facebook.com/docs/threads)
- [Access Token Guide](https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions)
- [Meta Developer Console](https://developers.facebook.com/)

---

**После обновления токена приложение заработает автоматически!** 🎉
