import openai
import telegram
import asyncio
import datetime
import logging
import re
import fitz  # PyMuPDF для работы с PDF

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Функция для извлечения текста из PDF
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text
    except Exception as e:
        logging.error(f"Ошибка при чтении PDF: {e}")
        return ""

# Функция для загрузки текста из TXT или PDF
def load_book_text(file_path):
    try:
        if file_path.lower().endswith(".pdf"):
            return extract_text_from_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
    except Exception as e:
        logging.error(f"Ошибка при загрузке книги: {e}")
        return ""

# Функции сохранения/загрузки последней обработанной главы
def save_last_processed_chapter(file_path, last_chapter):
    with open(file_path, 'w') as file:
        file.write(str(last_chapter))

def load_last_processed_chapter(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            return int(content) if content else 0
    except (FileNotFoundError, ValueError):
        return 0

# Разбиение книги на главы
def split_book_into_parts(book_text):
    chapter_pattern = re.compile(r'Глава\s+([0-9]+|[IVXLCDM]+)\s*', re.IGNORECASE)
    chapters = chapter_pattern.split(book_text)[1:]
    return [chapters[i] + chapters[i+1] for i in range(0, len(chapters), 2)]

# Ограничение длинны текста
def trim_text_to_tokens(text, max_tokens=8000):
    words = text.split()
    trimmed_text = ""
    token_count = 0
    for word in words:
        if token_count + len(word) + 1 > max_tokens:
            break
        trimmed_text += word + " "
        token_count += len(word) + 1
    return trimmed_text.strip()

# Функция для вычисления времени до следующего сообщения
def time_until_next_message(hour, minute):
    now = datetime.datetime.utcnow()
    next_message_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now > next_message_time:
        next_message_time += datetime.timedelta(days=1)
    return (next_message_time - now).total_seconds()

# Асинхронная функция для отправки сообщения в Telegram
async def send_message_to_telegram_channel(text, bot_token, channel_id):
    if not text:
        logging.warning("Попытка отправить пустое сообщение в Telegram")
        return
    try:
        bot = telegram.Bot(token=bot_token)
        await bot.send_message(chat_id=channel_id, text=text)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

# Генерация краткого содержания книги
def generate_summary(text):
    try:
        openai.api_key = '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'  # Укажи свой API-ключ
        prompt_text = "Ты — профессиональный инвестиционный аналитик и финансовый консультант. Твоя задача — обучать владельца инвестиционного фонда ключевым знаниям из книги. Анализируй каждую главу через призму asset management, определяй ключевые идеи и стратегии, приводи примеры их применения, формулируй практические выводы, которые можно внедрить в инвестиционную стратегию. Объясняй простыми словами, избегая сложного жаргона. Отвечай в формате: краткое изложение главы, основные идеи, практические выводы, рекомендации для владельца фонда. Пиши текст в формате образовательного эссе, как будто проводишь персональную консультацию."

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": text}
            ],
            max_tokens=2000
        )
        last_message = response['choices'][0]['message']['content']
        logging.info(f"Сгенерированное краткое содержание: {last_message[:50]}...")
        return last_message.strip()
    except Exception as e:
        logging.error(f"Ошибка при генерации краткого содержания: {e}")
        return None

# Основная функция обработки книг
async def process_books(file_path1, file_path2, bot_token, channel_id):
    try:
        # Загружаем последние обработанные главы
        last_processed_chapter1 = load_last_processed_chapter("last_processed_chapter1.txt")
        last_processed_chapter2 = load_last_processed_chapter("last_processed_chapter2.txt")

        # Загружаем текст книг (TXT или PDF)
        book_text1 = load_book_text(file_path1)
        book_text2 = load_book_text(file_path2)

        # Разбиваем книги на главы
        chapters1 = split_book_into_parts(book_text1)
        chapters2 = split_book_into_parts(book_text2)

        # Отправляем сообщение о старте работы бота
        start_message = "Бот для анализа книг и отправки пересказов запущен!"
        await send_message_to_telegram_channel(start_message, bot_token, channel_id)

        # Расписание отправки сообщений (по UTC)
        schedule = [(11, 00)]  # 13:00 EET = 11:00 UTC

        # Обрабатываем главы книг по очереди
        for (chapter_number1, chapter_text1), (chapter_number2, chapter_text2) in zip(enumerate(chapters1, start=1), enumerate(chapters2, start=1)):
            if chapter_number1 > last_processed_chapter1:
                trimmed_text1 = trim_text_to_tokens(f"Глава {chapter_number1}\n{chapter_text1}")
                summary1 = generate_summary(trimmed_text1)
                if summary1:
                    await send_message_to_telegram_channel(summary1, bot_token, channel_id)
                await asyncio.sleep(time_until_next_message(*schedule[0]))
                save_last_processed_chapter("last_processed_chapter1.txt", chapter_number1)

            if chapter_number2 > last_processed_chapter2:
                trimmed_text2 = trim_text_to_tokens(f"Глава {chapter_number2}\n{chapter_text2}")
                summary2 = generate_summary(trimmed_text2)
                if summary2:
                    await send_message_to_telegram_channel(summary2, bot_token, channel_id)
                await asyncio.sleep(time_until_next_message(*schedule[0]))
                save_last_processed_chapter("last_processed_chapter2.txt", chapter_number2)

    except Exception as e:
        logging.error(f"Ошибка во время обработки книг: {e}")

# Запуск бота
file_path1 = "emerald.pdf"
file_path2 = "berkley.pdf"
bot_token = '6786746440:AAF2yGdkXhWdnPRzkYZDz1-gweckuTUp-ss'
channel_id = '@rheniumbooks'

asyncio.run(process_books(file_path1, file_path2, bot_token, channel_id))
