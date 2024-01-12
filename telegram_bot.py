import os
import logging
from datetime import datetime
from functools import partial
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from translator import translate_text

# Настройка логирования
logging.basicConfig(
    filename='bot.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Установка ключа API для OpenAI из переменной окружения
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Функция для парсинга новостей
def parse_news(url):
    try:
        logger.info(f"Запрос к URL: {url}")
        response = requests.get(url)
        response.raise_for_status()  # Убедитесь, что запрос прошел успешно
        soup = BeautifulSoup(response.content, 'html.parser')

        articles = []
        for article in soup.find_all('div', class_='collection-item-6'):
            # Найти дату новости
            date_div = article.find('div', class_='text-block-30')
            date_text = date_div.text.strip() if date_div else 'Дата отсутствует'

            # Найти заголовок новости
            title_div = article.find('div', class_='text-block-27')
            title_text = title_div.text.strip() if title_div else 'Нет заголовка'

            # Найти домен источника новости
            source_div = article.find('div', class_='text-block-28')
            source_text = source_div.text.strip() if source_div else 'Нет источника'

            # Найти URL изображения
            image = article.find('img')
            image_url = image['src'] if image and 'src' in image.attrs else 'URL изображения отсутствует'

            # Собрать URL новости
            news_url = article.a['href'] if article.a and 'href' in article.a.attrs else 'URL новости отсутствует'

            articles.append({
                'date': date_text,
                'title': title_text,
                'source': source_text,
                'image_url': image_url,
                'news_url': news_url
            })

        logger.info(f"Найдено {len(articles)} новостей")
        return articles
    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}")
        return []


# Функция для отправки запроса на генерацию комментария от эксперта
def generate_expert_commentary(news_text):
    try:
        response = openai_client.Completion.create(
            model="text-davinci-002",
            prompt=f"Экспертный комментарий\n\n{news_text}\n\nКомментарий:",
            max_tokens=100
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Ошибка при генерации экспертного комментария: {str(e)}")
        return "Произошла ошибка при генерации комментария."


# Функция для отправки новости и комментария в Telegram
def send_news(context: CallbackContext):
    try:
        channel_name = os.getenv('TELEGRAM_CHANNEL_NAME', '@your_default_channel_name')
        logger.info(f"Начало отправки новостей в канал {channel_name}")
        url = 'https://www.futuretools.io/news'
        articles = parse_news(url)

        if not articles:
            logger.info("Новостей для отправки нет.")
            return

        last_published_article_file = 'last_published_article.txt'
        latest_article_date = datetime.min

        for article in articles:
            article_date = datetime.strptime(article['date'], '%B %d, %Y')
            if is_new_article(article_date, last_published_article_file):
                original_title = article['title']
                target_language = 'en'  # Или любой другой язык, на который вы хотите перевести

                # Переводим заголовок статьи
                translated_title = translate_text(original_title, target_language)

                source = article['source']
                news_url = article['news_url']
                image_url = article['image_url']

                # Строим текст новости с использованием переведенного заголовка
                news_text = f"{translated_title}\nИсточник: {source}\n[Читать далее]({news_url})\n![image]({image_url})"
                logger.info(f"Обнаружена новая статья для отправки: {translated_title}")

                expert_commentary = generate_expert_commentary(news_text)
                if expert_commentary:
                    message = f"{news_text}\n\nЭкспертный комментарий:\n{expert_commentary}"
                else:
                    message = news_text

                try:
                    context.bot.send_message(chat_id=channel_name, text=message, parse_mode='Markdown')
                    logger.info(f"Новость отправлена: {translated_title}")
                    latest_article_date = max(latest_article_date, article_date)
                except Exception as e:
                    logger.error(f"Ошибка при отправке новости {translated_title}: {e}")
            else:
                logger.info("Статья не прошла проверку is_new_article и не будет отправлена.")

        if latest_article_date > datetime.min:
            update_last_published_article(latest_article_date, last_published_article_file)
            logger.info(f"Дата последней опубликованной новости обновлена: {latest_article_date.strftime('%B %d, %Y')}")

        logger.info("Завершение отправки новостей")
    except Exception as e:
        logger.error(f"Произошла ошибка при отправке новостей: {str(e)}")

# Функция для проверки, является ли статья новой
def is_new_article(article_date, last_published_article_file):
    try:
        with open(last_published_article_file, 'r') as file:
            last_published_date_str = file.read().strip()
            last_published_date = datetime.strptime(last_published_date_str, '%B %d, %Y') if last_published_date_str else datetime.min
        logger.info(f"Последняя опубликованная дата: {last_published_date}")
        logger.info(f"Дата статьи: {article_date}")
        return article_date > last_published_date
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {last_published_article_file}: {e}")
        return False

# Функция для обновления даты последней опубликованной статьи
def update_last_published_article(article_date, last_published_article_file):
    try:
        with open(last_published_article_file, 'w') as file:
            logger.info(f"Обновление файла {last_published_article_file} с датой {article_date.strftime('%B %d, %Y')}")
            file.write(article_date.strftime('%B %d, %Y'))
            logger.info(f"Файл {last_published_article_file} обновлен с датой {article_date.strftime('%B %d, %Y')}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении файла {last_published_article_file}: {e}")

# Функция для ручной отправки новостей
def manual_send_news(update, context: CallbackContext):
    send_news(context)

# Функция для запуска бота
# Функция для запуска бота
def main():
    try:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        updater = Updater(token)  # Изменено здесь

        dp = updater.dispatcher
        dp.add_handler(CommandHandler('sendnews', manual_send_news))

        # Настройка планировщика для регулярной отправки новостей
        scheduler = BackgroundScheduler(timezone=pytz.utc)
        job = partial(send_news, context=updater.job_queue)
        scheduler.add_job(job, 'interval', minutes=3)
        scheduler.start()

        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {str(e)}")

if __name__ == '__main__':
    main()

