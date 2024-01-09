import openai
import telegram
import asyncio
import datetime
import logging
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)

def save_last_processed_chapter(file_path, last_chapter):
    with open(file_path, 'w') as file:
        file.write(str(last_chapter))

def load_last_processed_chapter(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            # Проверяем, не пустой ли файл
            if content:
                return int(content)
            else:
                return 0
    except (FileNotFoundError, ValueError):
        # Возвращаем 0, если файл не найден или содержит некорректные данные
        return 0

# Функция для разбиения текста книги на книги и главы
def split_book_into_parts(book_text):
    # Используем регулярное выражение для поиска глав
    chapter_pattern = re.compile(r'Глава\s+([0-9]+|[IVXLCDM]+)\s*', re.IGNORECASE)
    chapters = chapter_pattern.split(book_text)[1:]
    return [chapters[i] + chapters[i+1] for i in range(0, len(chapters), 2)]

# Функция для ограничения длинны текста
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


# Функция для определения времени до следующего запланированного сообщения
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

# Функция для генерации краткого содержания
def generate_summary(text):
    try:
        openai.api_key = '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'
        response = openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "Вы публицист, экономист, правый либертарианец, капиталист, который читает книги и пишет блог в повествовательном стиле. Ваша задача - проанализировать и пересказать в доступной манере, предоставленный текст из книг по экономике. Начиная, в первой фразе упоминайте номер главы (номер всегда после слова ГЛАВА), ее название и упоминайте автора и название книги - они указаны в самом начале файла (Автор:, Книга:). Уложитесь в 300 слов. Пишите грамотно на украинском языке, в сдержанном публицистическом стиле, не используйте сложных словесных конструкций."},
                {"role": "user", "content": text}
            ],
            max_tokens=2000
        )
        last_message = response['choices'][0]['message']['content']
        logging.info(f"Сгенерированное краткое содержание: {last_message[:50]}...")  # Логируем начало сообщения
        return last_message.strip()
    except Exception as e:
        logging.error(f"Ошибка при генерации краткого содержания: {e}")
        return None  # Возвращаем None в случае ошибки

    
# Основная функция
async def process_books(file_path1, file_path2, bot_token, channel_id):
    try:
        # Загрузка последней обработанной главы для каждой книги
        last_processed_chapter1 = load_last_processed_chapter("last_processed_chapter1.txt")
        last_processed_chapter2 = load_last_processed_chapter("last_processed_chapter2.txt")
        
        # Чтение и разбиение первой книги
        with open(file_path1, 'r', encoding='utf-8') as file:
            book_text1 = file.read()
        chapters1 = split_book_into_parts(book_text1)

        # Чтение и разбиение второй книги
        with open(file_path2, 'r', encoding='utf-8') as file:
            book_text2 = file.read()
        chapters2 = split_book_into_parts(book_text2)

        # Отправка начального сообщения
        start_message = "Бот для анализа книг и отправки пересказов запущен!"
        await send_message_to_telegram_channel(start_message, bot_token, channel_id)

        # Расписание отправки сообщений
        schedule = [(11,00), (17, 00), (18,00)]  # (час, минута)
        schedule_index = 0

        # Чередование между книгами
        for (chapter_number1, chapter_text1), (chapter_number2, chapter_text2) in zip(enumerate(chapters1, start=1), enumerate(chapters2, start=1)):
            if chapter_number1 > last_processed_chapter1:
                # Обработка главы из первой книги
                trimmed_text1 = trim_text_to_tokens(f"Глава {chapter_number1}\n{chapter_text1}")
                summary1 = generate_summary(trimmed_text1)
                if summary1:
                    await send_message_to_telegram_channel(summary1, bot_token, channel_id)
                else:
                    logging.warning(f"Получен пустой текст для главы {chapter_number1} из первой книги")
                await asyncio.sleep(time_until_next_message(*schedule[schedule_index]))
                schedule_index = (schedule_index + 1) % len(schedule)
                save_last_processed_chapter("last_processed_chapter1.txt", chapter_number1)

            if chapter_number2 > last_processed_chapter2:
                # Обработка главы из второй книги
                trimmed_text2 = trim_text_to_tokens(f"Глава {chapter_number2}\n{chapter_text2}")
                summary2 = generate_summary(trimmed_text2)
                if summary2:
                    await send_message_to_telegram_channel(summary2, bot_token, channel_id)
                else:
                    logging.warning(f"Получен пустой текст для главы {chapter_number2} из второй книги")
                await asyncio.sleep(time_until_next_message(*schedule[schedule_index]))
                schedule_index = (schedule_index + 1) % len(schedule)
                save_last_processed_chapter("last_processed_chapter2.txt", chapter_number2)

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")


# Пример использования
file_path1 = "745514.txt"
file_path2 = "book-bot.txt"
bot_token = '6786746440:AAF2yGdkXhWdnPRzkYZDz1-gweckuTUp-ss'
channel_id = '@rheniumbooks'

asyncio.run(process_books(file_path1, file_path2, bot_token, channel_id))
