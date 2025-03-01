import json
import logging
import hashlib
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from googletrans import Translator, LANGUAGES

logger = logging.getLogger(__name__)


class TranslationMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.translator = Translator()
        self.CACHE_TIMEOUT = getattr(settings, 'TRANSLATION_CACHE_TIMEOUT', 60 * 60 * 24)  # 24 часа по умолчанию
        self.MAX_TEXT_LENGTH = getattr(settings, 'TRANSLATION_MAX_LENGTH', 5000)  # максимальная длина текста
        self.BATCH_SIZE = getattr(settings, 'TRANSLATION_BATCH_SIZE', 10)  # размер пакета для перевода

    def process_response(self, request, response):
        if not getattr(settings, 'TRANSLATION_ENABLED', True):
            return response

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response

        user_language = getattr(request.user, 'language', None)
        if user_language:
            user_language = getattr(user_language, 'code', settings.TRANSLATION_DEFAULT_LANGUAGE)
        else:
            user_language = settings.TRANSLATION_DEFAULT_LANGUAGE

        if not user_language or user_language == settings.TRANSLATION_DEFAULT_LANGUAGE:
            return response

        if user_language not in LANGUAGES:
            logger.warning(f"Язык {user_language} не поддерживается Google Translate")
            return response

        if 'application/json' in response.get('Content-Type', ''):
            try:
                data = json.loads(response.content.decode('utf-8'))
                translated_data = self.translate_data(data, user_language)
                response.content = json.dumps(translated_data, ensure_ascii=False).encode('utf-8')
            except Exception as e:
                logger.error(f"Ошибка перевода JSON: {str(e)}")

        return response

    def translate_data(self, data, target_language):
        """ Переводит данные JSON, исключая технические поля и None """
        if data is None:
            return data

        try:
            if isinstance(data, str):
                if not data.strip() or self.is_excluded_field(data) or len(data) > self.MAX_TEXT_LENGTH:
                    return data
                return self.get_translation(data, target_language)

            elif isinstance(data, list):
                return [self.translate_data(item, target_language) for item in data]

            elif isinstance(data, dict):
                return {key: self.translate_data(value, target_language) for key, value in data.items()}

            else:
                return data

        except Exception as e:
            logger.error(f"Ошибка перевода данных '{str(data)[:50]}...' типа {type(data)}: {str(e)}")
            return data

    def get_translation(self, text, target_language):
        """ Получение перевода с использованием кеширования """
        if not text or not isinstance(text, str) or len(text) > self.MAX_TEXT_LENGTH:
            return text

        cache_key = f"trans_{hashlib.md5((text + target_language).encode()).hexdigest()}"

        cached_translation = cache.get(cache_key)
        if cached_translation:
            return cached_translation

        try:
            result = self.translator.translate(text, dest=target_language)
            translated_text = result.text if hasattr(result, 'text') else text

            cache.set(cache_key, translated_text, self.CACHE_TIMEOUT)

            return translated_text
        except Exception as e:
            logger.error(f"Ошибка перевода '{text[:100]}...': {str(e)}")
            return text

    def is_excluded_field(self, value):
        """ Исключаем технические поля из перевода """
        if not isinstance(value, str):
            return True

        EXCLUDED_KEYWORDS = getattr(settings, 'TRANSLATION_EXCLUDED_KEYWORDS',
                                    ['url', 'slug', 'id', 'price', 'year', 'latitude',
                                     'longitude', 'rating', 'email', 'phone', 'http://', 'https://'])

        if len(value.strip()) < 3 or value.startswith(('http://', 'https://')):
            return True

        return any(keyword in value.lower() for keyword in EXCLUDED_KEYWORDS)
