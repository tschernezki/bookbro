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

# Функция для определения времени до следующего запланированного сообщения (для тестирования)
def time_until_next_message_test():
    return 120  # задержка в 120 секунд

# Асинхронная функция для отправки сообщения в Telegram
async def send_message_to_telegram_channel(text, bot_token, channel_id):
    bot = telegram.Bot(token=bot_token)
    await bot.send_message(chat_id=channel_id, text=text)

# Функция для генерации краткого содержания
def generate_summary(text):
    openai.api_key = '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'
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": "Вы публицист, экономист и историк, который читает книгу и пишет блог в повествовательном стиле. Ваша задача - проанализировать и пересказать в доступной манере, предоставленный текст из книги. Начиная текст, придумайте фразу вроде 'Анализируя прочитанное, я заметил ...' или 'Продолжая читать книгу, обнаружил интересные мысли...' и в этой фразе упоминайте главу, которую читаете - ее номер или название и упоминайте автора и название книги. Уложитесь в 250 слов."},
            {"role": "user", "content": text}
        ],
        max_tokens=1000
    )
    last_message = response['choices'][0]['message']['content']
    return last_message.strip()

async def process_book_test(file_path, bot_token, channel_id):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            book_text = file.read()

        chapters = split_book_into_parts(book_text)

        for chapter_number, chapter_text in enumerate(chapters, start=1):
            logging.info(f"Обработка главы {chapter_number}")
            summary = generate_summary(f"Глава {chapter_number}\n{chapter_text}")
            await send_message_to_telegram_channel(summary, bot_token, channel_id)
            await asyncio.sleep(time_until_next_message_test())  # Задержка в 120 секунд для тестирования
    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")


# Пример использования для тестирования
file_path = "book-bot.txt"
bot_token = '6786746440:AAF2yGdkXhWdnPRzkYZDz1-gweckuTUp-ss'
channel_id = '@rheniumbooks'

# Запуск основной функции
if __name__ == "__main__":
    asyncio.run(process_book_test(file_path, bot_token, channel_id))
