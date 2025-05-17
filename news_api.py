import requests
import hashlib
import logging
from datetime import datetime
from data.news import News
from data.db_session import create_session
import uuid
logger = logging.getLogger(__name__)


class NewsAggregator:
    def __init__(self):
        self.API_KEYS = {
            'newsapi': 'c4eb4625b08343aebafeb27f8ef9b9ee',
            'guardian': '653e89bb-bfa3-43bd-b25c-1e78fb61d667'
        }

    def fetch_news(self):
        """Основной метод загрузки новостей"""
        self._fetch_newsapi()
        self._fetch_guardian()

    def _fetch_newsapi(self):
        """NewsAPI запрос"""
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                'apiKey': self.API_KEYS['newsapi'],
                'country': 'us',
                'pageSize': 20
            }

            logger.debug(f"NewsAPI запрос: {url}")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                logger.info(f"NewsAPI: получено {len(response.json()['articles'])} статей")
                self._process_newsapi(response.json())
            else:
                logger.error(f"NewsAPI ошибка: {response.status_code}")

        except Exception as e:
            logger.error(f"NewsAPI критическая ошибка: {str(e)}", exc_info=True)

    def _process_newsapi(self, data):
        """Обработка NewsAPI данных"""
        db_sess = create_session()
        try:
            for article in data.get('articles', []):
                url_hash = hashlib.md5(article['url'].encode()).hexdigest()

                news = News(
                    title=article['title'][:255],
                    content=article['description'] or article['content'] or 'Нет описания',
                    source='NewsAPI',
                    tags=article.get('category', 'general'),
                    published_at=datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
                    api_id=url_hash
                )
                db_sess.merge(news)
            db_sess.commit()
        except Exception as e:
            logger.error(f"Ошибка обработки NewsAPI: {str(e)}")
            db_sess.rollback()
        finally:
            db_sess.close()
    def _fetch_guardian(self):
        """Загрузка данных The Guardian"""
        try:
            response = requests.get(
                "https://content.guardianapis.com/search",
                params={
                    'api-key': self.API_KEYS['guardian'],
                    'show-fields': 'trailText',
                    'page-size': 50,
                    'show-tags': 'keyword'
                },
                timeout=15
            )
            if response.ok:
                self._process_guardian(response.json())
            else:
                logger.error(f"Guardian error: {response.status_code}")
        except Exception as e:
            logger.error(f"Guardian failed: {str(e)}")

    def _process_guardian(self, data):
        """Обработка Guardian данных"""
        db_sess = create_session()
        try:
            for result in data.get('response', {}).get('results', []):
                try:
                    guardian_id = result.get('id', '')
                    api_id = hashlib.md5(guardian_id.encode()).hexdigest() if guardian_id else str(uuid.uuid4())

                    news = News(
                        title=result.get('webTitle', '')[:255],
                        content=result.get('fields', {}).get('trailText', '')[:512],
                        source='The Guardian',
                        tags=','.join([
                            tag['webTitle']
                            for tag in result.get('tags', [])[:3]
                        ])[:100],
                        published_at=datetime.strptime(
                            result['webPublicationDate'],
                            '%Y-%m-%dT%H:%M:%SZ'
                        ),
                        api_id=api_id,
                        url=f"https://www.theguardian.com/{guardian_id}"
                    )
                    db_sess.merge(news)
                except KeyError as e:
                    logger.error(f"Guardian format error: {str(e)}")
            db_sess.commit()
        finally:
            db_sess.close()
