import openai
import telegram
import telegram.ext
import asyncio
import datetime
import logging
import concurrent.futures
import httpx

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# Configure a longer timeout duration
timeout_config = httpx.Timeout(10.0)  # 10 seconds timeout

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# Асинхронная функция для генерации краткого содержания
async def generate_summary(text):
    openai.api_key = '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'

    headers = {
        'Authorization': f'Bearer {openai.api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "Вы публицист, экономист, и убежденный либертарианец-капиталист, который читает книги и пишет блог в повествовательном стиле. Ваша задача - проанализировать и пересказать в доступной манере, предоставленный текст из книги, сравнивая описываемое в каждой главе, с экономическими и социальными реалиями 21 века. Начиная, придумайте фразу вроде 'Анализируя прочитанное, я заметил ...' или 'Читая книгу, обнаружил интересные мысли...' и во фразе упоминайте номер главы, которую прочли, ее название и упоминайте автора и название книги. Уложитесь в 300 слов. Пишите на украинском языке, в разговорном но не фамильярном стиле."},
            {"role": "user", "content": text}
        ],
        "max_tokens": 1000
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions', 
                json=payload, 
                headers=headers
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
    except httpx.HTTPStatusError as exc:
        logging.error(f"HTTP error occurred: {exc}")
    except httpx.RequestError as exc:
        logging.error(f"An error occurred while requesting: {exc}")
    except httpx.TimeoutException:
        logging.error("The request timed out while contacting the OpenAI API.")

    return None  # В случае ошибки возвращаем None или можете выбросить исключение
    
# Основная функция
async def process_book(file_path, bot_token, channel_id):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            book_text = file.read()

        chapters = split_book_into_parts(book_text)

        # Отправка сообщения о начале работы бота
        start_message = "Бот для анализа книги и отправки пересказов запущен!"
        await send_message_to_telegram_channel(start_message, bot_token, channel_id)
        logging.info("Отправлено начальное сообщение в канал")  # Логирование отправки начального сообщения

        # Расписание отправки сообщений
        schedule = [(9, 0), (15, 30), (17, 00)]
        schedule_index = 0

        for chapter_number, chapter_text in enumerate(chapters, start=1):
            trimmed_text = trim_text_to_tokens(f"Глава {chapter_number}\n{chapter_text}")
            summary = generate_summary(trimmed_text)
            await send_message_to_telegram_channel(summary, bot_token, channel_id)
            logging.info(f"Отправлена глава {chapter_number}")  # Логирование отправки каждой главы

            await asyncio.sleep(time_until_next_message(*schedule[schedule_index]))
            schedule_index = (schedule_index + 1) % len(schedule)

    except Exception as e:
        logging.error(f"Произошла ошибка при обработке книги: {e}")
        
# Асинхронная функция для обработки входящих сообщений от пользователя в Telegram
async def process_user_messages_async(bot_token, update_queue):
    # Инициализируем application и обработчики сообщений
    application = Application.builder().token(bot_token).update_queue(update_queue).build()

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_text = update.message.text
            logging.info(f"Получено сообщение: {user_text}")
            summary = await generate_summary(user_text)  # Использование await для асинхронного вызова
            logging.info("Сгенерирован ответ")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=summary)
            logging.info("Ответ отправлен пользователю")
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения пользователя: {e}")

    application.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Инициализируем обработчики без запуска цикла событий
    await application.initialize()
    return application

    
# Основная функция, запускающая обе задачи
async def main(file_path, bot_token, channel_id):
    # Создаём очередь обновлений для Application
    update_queue = asyncio.Queue()
    
    # Инициализируем Application и запускаем обработку книги
    application = await process_user_messages_async(bot_token, update_queue)
    book_task = asyncio.create_task(process_book(file_path, bot_token, channel_id))
    
    # Запускаем все задачи
    await asyncio.gather(book_task, application.idle())
    
# Пример использования
file_path = "book-bot.txt"  # Используйте относительный путь
bot_token = '6786746440:AAF2yGdkXhWdnPRzkYZDz1-gweckuTUp-ss'
channel_id = '@rheniumbooks'

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(main(file_path, bot_token, channel_id))
    else:
        try:
            loop.run_until_complete(main(file_path, bot_token, channel_id))
        finally:
            if loop.is_running():
                loop.close()
