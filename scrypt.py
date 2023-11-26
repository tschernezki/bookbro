import openai
import telegram
import asyncio
import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Функция для разбиения текста книги на книги и главы
def split_book_into_parts(book_text):
    parts = book_text.split("Книга ")
    chapters = []
    for part in parts[1:]:
        chapters.extend(part.split("Глава ")[1:])
    return chapters

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
    try:
        bot = telegram.Bot(token=bot_token)
        await bot.send_message(chat_id=channel_id, text=text)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

# Функция для генерации краткого содержания
def generate_summary(text):
    openai.api_key = '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'
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Вы публицист, экономист, и убежденный правый либертарианец-капиталист, который читает книги и пишет блог в повествовательном стиле. Ваша задача - проанализировать и пересказать в доступной манере, предоставленный текст из книги, сравнивая описываемое в каждой главе, с экономическими и социальными реалиями 21 века. Начиная, придумайте фразу вроде 'Анализируя прочитанное, я заметил ...' или 'Читая книгу, обнаружил интересные мысли...' и во фразе упоминайте номер главы, которую прочли, ее название и упоминайте автора и название книги. Уложитесь в 300 слов. Пишите на украинском языке, в разговорном но не фамильярном стиле."},
            {"role": "user", "content": text}
        ],
        max_tokens=1000
    )
    last_message = response['choices'][0]['message']['content']
    return last_message.strip()
    
# Основная функция
async def process_book(file_path, bot_token, channel_id):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            book_text = file.read()

        chapters = split_book_into_parts(book_text)

        # Отправка сообщения о начале работы бота
        start_message = "Бот для анализа книги и отправки пересказов запущен!"
        await send_message_to_telegram_channel(start_message, bot_token, channel_id)

        # Расписание отправки сообщений
        schedule = [(15, 30), (17, 00)]  # (час, минута)
        schedule_index = 0

        for chapter_number, chapter_text in enumerate(chapters, start=1):
            trimmed_text = trim_text_to_tokens(f"Глава {chapter_number}\n{chapter_text}")
            summary = generate_summary(trimmed_text)
            await send_message_to_telegram_channel(summary, bot_token, channel_id)

            # Ждать до следующего времени в расписании
            await asyncio.sleep(time_until_next_message(*schedule[schedule_index]))
            schedule_index = (schedule_index + 1) % len(schedule)

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")


# Пример использования
file_path = "book-bot.txt"  # Используйте относительный путь
bot_token = '6786746440:AAF2yGdkXhWdnPRzkYZDz1-gweckuTUp-ss'
channel_id = '@rheniumbooks'

asyncio.run(process_book(file_path, bot_token, channel_id))
