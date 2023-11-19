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

# Функция для определения времени до следующего запланированного сообщения
def time_until_next_message(hour):
    now = datetime.datetime.utcnow()
    next_message_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if now > next_message_time:
        next_message_time += datetime.timedelta(days=1)
    return (next_message_time - now).total_seconds()

# Асинхронная функция для отправки сообщения в Telegram
async def send_message_to_telegram_channel(text, bot_token, channel_id):
    bot = telegram.Bot(token=bot_token)
    await bot.send_message(chat_id=channel_id, text=text)

# Функция для генерации краткого содержания
def generate_summary(text):
    openai.api_key = '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'
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Вы публицист, экономист и историк, который читает книгу и пишет блог в повествовательном стиле. Ваша задача - проанализировать и пересказать в доступной манере, предоставленный текст из книги. Начиная текст, придумайте фразу вроде 'Анализируя прочитанное, я заметил ...' или 'Продолжая читать книгу, обнаружил интересные мысли...' и в этой фразе упоминайте главу, которую читаете - ее номер или название и упоминайте автора и название книги. Уложитесь в 250 слов."},
            {"role": "user", "content": text}
        ],
        max_tokens=1000
    )
    last_message = response['choices'][0]['message']['content']
    return last_message.strip()

# Основная функция
async def process_book(file_path, bot_token, channel_id):
    with open(file_path, 'r', encoding='utf-8') as file:
        book_text = file.read()

    chapters = split_book_into_parts(book_text)

    for chapter_number, chapter_text in enumerate(chapters, start=1):
        summary = generate_summary(f"Глава {chapter_number}\n{chapter_text}")
        await send_message_to_telegram_channel(summary, bot_token, channel_id)
        if chapter_number % 2 == 0:
            await asyncio.sleep(time_until_next_message(16))  # Отправка в 16:00 UTC
        else:
            await asyncio.sleep(time_until_next_message(9))   # Отправка в 09:00 UTC

# Пример использования
file_path = "book-bot.txt"
bot_token = '6786746440:AAF2yGdkXhWdnPRzkYZDz1-gweckuTUp-ss'
channel_id = '@rheniumbooks'

asyncio.run(process_book(file_path, bot_token, channel_id))
