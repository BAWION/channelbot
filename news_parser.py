import requests
from bs4 import BeautifulSoup
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

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

# Пример использования функции
if __name__ == '__main__':
    url = 'https://www.futuretools.io/news'
    news_articles = parse_news(url)
    for article in news_articles:
        print(f"Дата: {article['date']}")
        print(f"Заголовок: {article['title']}")
        print(f"Источник: {article['source']}")
        print(f"URL изображения: {article['image_url']}")
        print(f"URL новости: {article['news_url']}\n")
