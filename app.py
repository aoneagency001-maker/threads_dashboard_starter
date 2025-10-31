import streamlit as st
import json
from pathlib import Path
from backend.parser import process_book, QUOTES_DIR, BOOKS_DIR
from backend.agent import refine_quotes, harvest_all_from_pdf, improve_existing_quotes
import requests
import os
from dotenv import load_dotenv

load_dotenv()
ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

def publish_to_threads(caption: str) -> bool:
    """Публикует текстовый пост в Threads через Instagram Graph API."""
    if not ACCESS_TOKEN or not IG_USER_ID:
        st.error("❌ Токен Threads не найден. Добавь его в .env файл.")
        return False

    create_media = requests.post(
        f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media",
        data={"caption": caption, "access_token": ACCESS_TOKEN}
    ).json()

    if "id" not in create_media:
        st.error(f"Ошибка создания контейнера поста: {create_media}")
        return False

    creation_id = create_media["id"]

    publish = requests.post(
        f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media_publish",
        data={"creation_id": creation_id, "access_token": ACCESS_TOKEN}
    ).json()

    if "id" in publish:
        st.success("✅ Пост успешно опубликован в Threads!")
        return True
    else:
        st.error(f"Ошибка публикации: {publish}")
        return False

st.set_page_config(page_title="Quotes Extractor", page_icon="📚", layout="wide")
st.title("📚 База цитат из книг")

with st.sidebar:
    st.header("Источник книги")
    pdf_files = sorted([p for p in BOOKS_DIR.glob("*.pdf")])
    pdf_names = [p.name for p in pdf_files]
    selected_name = st.selectbox("Выберите PDF", options=pdf_names)
    query = st.text_input("Поиск по цитатам/переводу/смыслу", "")
    
    col1, col2 = st.columns(2)
    with col1:
        insights_btn = st.button("🔥 Собрать лучшие цитаты (GPT-инсайты)", type="primary")
    with col2:
        improve_btn = st.button("🧠 Улучшить существующие цитаты", type="secondary")

content_col, preview_col = st.columns([2, 1])

if selected_name:
    selected_pdf = BOOKS_DIR / selected_name
    quotes_json_path = QUOTES_DIR / (Path(selected_name).stem.replace(" ", "-") + ".json")

    if insights_btn:
        with st.spinner("🤖 Анализирую книгу и создаю осмысленные цитаты..."):
            out = harvest_all_from_pdf(str(selected_pdf))
        st.success(f"✅ Готово! Создано структурированных цитат: {out}")
        st.rerun()
    
    if improve_btn:
        if quotes_json_path.exists():
            with st.spinner("🧠 Улучшаю существующие цитаты с помощью умного анализа..."):
                out = improve_existing_quotes(str(quotes_json_path))
            st.success(f"✅ Готово! Улучшены цитаты: {out}")
            st.rerun()
        else:
            st.warning("Сначала соберите цитаты с помощью кнопки 'Собрать лучшие цитаты'")

    if quotes_json_path.exists():
        with open(quotes_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            data = payload.get("quotes", []) if isinstance(payload, dict) else payload
    else:
        data = []

    # Поиск/фильтр
    if query:
        q = query.lower()
        def match(item: dict) -> bool:
            return any(
                q in (item.get(k, "") or "").lower()
                for k in ("quote", "translated", "summary", "original")
            )
        filtered = [it for it in data if match(it)]
    else:
        filtered = data

    with content_col:
        st.subheader("Цитаты")
        if not filtered:
            st.info("📚 Нет данных. Нажмите 'Собрать лучшие цитаты' для анализа книги.")
        else:
            # Показываем статистику
            engaging_count = len([item for item in filtered if item.get("engaging") is True])
            improved_count = len([item for item in filtered if item.get("meta", {}).get("improved") is True])
            st.metric("📊 Всего цитат", len(filtered), f"Осмысленных: {engaging_count}, Улучшенных: {improved_count}")
            
            # Пагинация по 5 цитат
            per_page = 5
            total = len(filtered)
            total_pages = (total + per_page - 1) // per_page if total else 1
            page = st.number_input("Страница", min_value=1, max_value=max(total_pages, 1), value=1, step=1)
            start = (page - 1) * per_page
            end = start + per_page
            
            for i, item in enumerate(filtered[start:end], start=start + 1):
                # Показываем все цитаты, но выделяем engaging
                display_text = item.get('quote', '') or item.get('translated', '') or item.get('original', '')
                if not display_text:
                    continue
                    
                # Выделяем engaging цитаты и улучшенные
                meta = item.get("meta", {})
                is_improved = meta.get("improved", False)
                is_engaging = item.get("engaging") is True
                
                if is_engaging and is_improved:
                    st.markdown(f"**{i}.** 🔥🧠 {display_text}")
                elif is_engaging:
                    st.markdown(f"**{i}.** 🔥 {display_text}")
                elif is_improved:
                    st.markdown(f"**{i}.** 🧠 {display_text}")
                else:
                    st.markdown(f"**{i}.** ✍️ {display_text}")
                
                # Метаданные
                meta_line = []
                if item.get("category"):
                    meta_line.append(f"📂 {item.get('category')}")
                if item.get("style"):
                    meta_line.append(f"🎯 {item.get('style')}")
                if meta.get("quote_type"):
                    meta_line.append(f"📝 {meta.get('quote_type')}")
                if meta.get("confidence"):
                    meta_line.append(f"🎯 {meta.get('confidence'):.2f}")
                if meta_line:
                    st.caption(" • ".join(meta_line))
                
                # Сводка
                summary = item.get("summary")
                if summary:
                    st.write(f"🧠 {summary}")
                
                # Дополнительная информация о качестве
                if meta.get("reasoning"):
                    with st.expander("🔍 Анализ качества"):
                        st.write(f"**Объяснение:** {meta.get('reasoning')}")
                        if meta.get("context_score"):
                            st.write(f"**Контекст:** {meta.get('context_score'):.2f}")
                        if meta.get("practical_value"):
                            st.write(f"**Практическая ценность:** {meta.get('practical_value'):.2f}")
                        if meta.get("completeness"):
                            st.write(f"**Завершенность:** {meta.get('completeness'):.2f}")
                
                # Страница
                page_num = item.get("page")
                if page_num:
                    st.caption(f"📄 стр. {page_num}")
                
                st.divider()

        if st.button("🚀 Опубликовать в Threads"):
            with st.spinner("Публикуем пост..."):
                selected = None
                # Ищем engaging цитату
                for it in filtered:
                    if it.get("engaging") is True and it.get("quote"):
                        selected = it.get("quote")
                        break
                # Если нет engaging, берём первую доступную
                if not selected and filtered:
                    selected = (filtered[0].get("quote") or filtered[0].get("translated") or "").strip()
                if selected:
                    publish_to_threads(selected)
                else:
                    st.warning("Нет цитат для публикации. Сначала собери цитаты.")

    with preview_col:
        st.subheader("Файл")
        st.caption(selected_pdf.name)
        st.write(f"Цитат: {len(data)}")
