# Quotes Extractor

Готовая система для извлечения, анализа и перевода цитат из книг (PDF) с интерфейсом Streamlit.

## Запуск

1) Установите зависимости:

```bash
pip install -r requirements.txt
```

2) Создайте файл `.env` в корне и добавьте ключ:

```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

3) Поместите PDF-файлы в `data/books/`.

4) Запустите приложение:

```bash
streamlit run app.py
```

## Возможности

- Извлечение осмысленных цитат (insights) при помощи GPT-4o-mini
- Перевод на русский, сохранение оригинала
- Сохранение JSON на книгу: `data/quotes/<book>.json`
- Поиск и пагинация в UI (5 на страницу)

## Структура JSON

```json
{
  "book": "DotCom Secrets",
  "quotes": [
    {
      "page": 12,
      "original": "...",
      "summary": "...",
      "quote": "...",
      "translated": "..."
    }
  ]
}
```


