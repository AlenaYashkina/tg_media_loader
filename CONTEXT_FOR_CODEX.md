# CONTEXT FOR CODEX — v2

## 0) Кто я и зачем этот файл
Я Алёна. 9 лет — светотехник/светодизайнер (архитектурный свет: AutoCAD, DIALux, Photoshop, 3ds Max). Живу в Батуми, Грузия. Сейчас активно перехожу в **LLM‑assisted Python‑автоматизацию**: делаю рабочие пайплайны под бизнес‑задачи с помощью ChatGPT/Codex и локальных моделей. Этот файл — чтобы ты (Codex/LLM) **понимал мой контекст, цели и правила игры**, когда помогаешь мне править код, приводить в порядок репозитории и готовить проекты под портфолио и отклики.

— Английский: B1–B2 (могу объясняться и презентовать в созвоне).  
— Формат работы: **удалёнка**, релокацию не ищу.  
— Цель: найти ремоут‑работу/контракты в зонах **AI‑automation / Prompt/LLM / Creative Tech**, без «чистого» энтерпрайз‑кодинга и только если есть работа с нейронками.  
— По деньгам: ориентир ≥ $1 000/мес (точнее $1 000-1 200/мес, можно выше).  
— Честность: **никакого «я senior dev»**. Я инженер автоматизации с ИИ: проектирую логику, пишу промпты, получаю и правлю код, довожу до результата, измеряю эффект, документирую.

## 1) Как меня позиционировать (коротко и честно)
**RU:** LLM‑assisted Python‑автоматизация: OCR/изображения/док‑генерация/скрапинг/Streamlit. Проекты из «хаоса входных данных → готовый отчёт/панель».  
**EN:** LLM‑assisted Python automation (OCR, image preprocessing, document generation, scraping, Streamlit). Turning messy inputs into clean deliverables.

### Мой стек (говорим так)
**LLM‑assisted stack:** Python (pandas, Pillow, *basic* OpenCV), Tesseract OCR (pytesseract), `python-pptx`/Excel, Telethon/Selenium по задаче, Streamlit UI, Git/GitHub, **Ollama + light LangChain**.  
Важно: я не пишу фреймворки «с нуля», **я умею читать/править/склеивать** с помощью LLM и проверять результат.

## 2) Анти‑«вайб‑кодинг»: требования к коду и репозиториям
1. **I/O контракт:** чёткие входы/выходы + CLI флаги (`--src --dst --start --end --dry-run --max-slides …`).  
2. **Идемпотентность:** повторный запуск безопасен, временные файлы/папки, атомарные записи.  
3. **Конфиги:** `.env.example`, `config.yaml`/`settings.py`; **без секретов в гите**.  
4. **Логи/метрики:** `INFO` — шаги пайплайна, `ERROR` — детали; счётчики времени и объёмов.  
5. **Зависимости:** `requirements.txt` с пиннутыми версиями; `pip install -r requirements.txt`.  
6. **Стиль:** понятные структуры, докстринги, читаемый код, кросс‑платформенность.  
7. **Тест‑минимум:** smoke-дataset в `sample/`, один «мини‑прогон» после правок.  
8. **README first:** цель → как запустить → демо → before/after → ограничения.  
9. **Windows/UTF-8:** пути, энкодинг, UTC, GPU‑фоллбек.  
10. **Market-friendly:** короткий Impact‑блок для откликов.

## 3) Ключевые проекты (фокус для портфолио)
### A) Photo-Report Generator
EXIF/OCR → подписи → штампы → PowerPoint. Уменьшает ручную работу примерно на 80–90% за сезон.  
Задачи: стабильная раскладка, один проход без повторов, метрики, README.

### B) Rent‑Finder (раз сейчас работаешь с этим репо)
Telegram → NDJSON/SQLite → LLM-структурирование. Нужно:
- строгое JSON-выход, фильтр по городу/стране, детект дублей (фото+simhash), FX/метрики.

### C) CLIP‑Clusterer
Группировка фото по смыслу, экспорты CSV/PDF, Streamlit UI. Сохраняем ручное исправление.

## 4) Гайд для Codex по правкам
- Не изобретай архитектуру, упрощай и стабилизируй.  
- Добавляй логи, явные исключения, проверку путей.  
- Предлагай 2–3 варианта с плюсами/минусами, если неясно.  
- Комментарии/докстринги — human-friendly.  
- Учитывай Windows‑пути, кириллицу и UTC.  
- RTX 2070 8 GB: GPU‑фоллбек обязателен.

## 5) Маркетинговые формулы (на выбор)
**EN (safe):** “LLM‑assisted Python automation. Built a production photo-report pipeline (EXIF/OCR → stamping → PowerPoint) and a Telegram rent parser with LLM post-processing and Streamlit social feed. Stack: Python (pandas, Pillow, basic OpenCV), Tesseract, python-pptx, Excel, Telethon/Selenium, Streamlit; LLMs via Ollama + light LangChain. Cut manual prep time by ~80–90%.”  
**RU (safe):** «LLM‑assisted автоматизация на Python: докекс фотоотчётов (EXIF/OCR → подписи → PowerPoint) и парсер аренды (LLM‑структурирование + Streamlit‑лента). Сократил ручной сбор примерно на 80–90%.»

## 6) Что **не** обещаем
- Никаких «Senior/ML Engineer/SOTA agents».  
- Только light handoff (скрипты/инструкции), не глубокий MLOps.  
- Не переписываем всё на «идеальные паттерны», если это ломает сроки.  
- Не тащим тяжёлые зависимости без нужды.

## 7) Критерии «готово» (Definition of Done)
- Скрипты запускаются одной командой, флаги понятны, README есть.  
- Есть `sample/` и минимальные прогон для проверки.  
- Логи показывают прогресс, ошибки ― информативны.  
- Повторный запуск не ломает результат.  
- README содержит «1‑минутное демо» и before/after.  
- Есть короткий Impact-блок (экономия/период/масштаб).

## 8) Текущие приоритеты (ближайшие итерации)
1. Photo-Report: убрать дубликаты/повторы, стабилизировать раскладку, добавить метрики/README.
2. Rent-Finder: строгий JSON, фильтры, метрики, новый LLM-эндпоинт.
3. CLIP-Clusterer: сохранение/экспорт, аккуратный UI.

— Затем: выкладываем на GitHub, описываем roadmap и готовим питчи под отклики.

## 9) Строгий JSON-схема и промпты

- **LLM handling:** вся семантика (языки, запросы, скоринг каналов, анализ объявления, price/rooms/pets, `notes`) берётся только из LLM. **Никаких регулярных выражений или эвристических парсеров**.
- **Схема `analysis`:** LLM отвечает строго одним JSON-объектом с такими ключами — `price`, `currency`, `rooms`, `bedrooms`, `bathrooms`, `pets_allowed`, `long_term`, `short_term`, `amenities`, `district`, `address`, `notes`. Любое отсутствие — `null` (или `[]` для `amenities`). Отдельно `notes` содержат маркеры вроде `location mismatch`, если город/страна не совпадают.
- **Кеш:** ответы LLM кешируются под `~/.rentgram_cache/{hash}.json` (можно переопределить через `RENTGRAM_CACHE`). Ключ — хеш prompt+model+function.
- **Примеры промптов:**
  1. *System:* “Экстрактор долгосрочной аренды жилья, возвращай только JSON по схеме {...}, если город неверный — помести `location mismatch` в notes.”  
     *User:* “City: Batumi, Country: Georgia, Text: 2BR flat in Batumi, 750$ monthly, pets allowed.”
  2. *System:* “Ты подтверждаешь, что в тексте указаны city/country и если нужно — помечаешь mismatch в notes. Добивайся структуры JSON без лишних строк.”  
     *User:* “City: Batumi, Country: Georgia, Text: Short-term loft in Tbilisi, 120 GEL/day.”  
  3. *System:* “Генерируй до 15 коротких запросов (2-6 слов) для Telegram global search по долгосрочной аренде и возвращай JSON {\"queries\": [...]}.”  
     *User:* “city=Batumi, country=Georgia, language=ru.”

Важное: если LLM не отвечает JSON, вернул `null`, пустую строку или неправильную структуру — мы **немедленно падаем** с `RuntimeError`, без обратного перехода на локальные эмпирики.
