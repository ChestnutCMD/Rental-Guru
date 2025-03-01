import json
import logging
import hashlib
import concurrent.futures
from RentalGuru import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from mtranslate import translate

logger = logging.getLogger(__name__)


class TranslationMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.CACHE_TIMEOUT = getattr(settings, 'TRANSLATION_CACHE_TIMEOUT', 60 * 60 * 24)
        self.MAX_WORKERS = getattr(settings, 'TRANSLATION_MAX_WORKERS', 2)

    def process_response(self, request, response):
        if not getattr(settings, 'TRANSLATION_ENABLED', True):
            return response

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response

        user_language = getattr(request.user, 'language', None)
        user_language = getattr(user_language, 'code', settings.TRANSLATION_DEFAULT_LANGUAGE) if user_language else settings.TRANSLATION_DEFAULT_LANGUAGE

        if not user_language or user_language == settings.TRANSLATION_DEFAULT_LANGUAGE:
            return response

        if 'application/json' in response.get('Content-Type', ''):
            try:
                data = json.loads(response.content.decode('utf-8'))
                strings_to_translate = {}

                self._extract_translatable_strings(data, strings_to_translate)

                if strings_to_translate:
                    translated_strings = self._translate_strings(strings_to_translate, user_language)
                    translated_data = self._apply_translations(data, translated_strings)
                else:
                    translated_data = data

                response.content = json.dumps(translated_data, ensure_ascii=False).encode('utf-8')
            except Exception as e:
                logger.error(f"Ошибка перевода JSON: {str(e)}")

        return response

    def _extract_translatable_strings(self, data, result, path=""):
        """Извлекает все строки, которые нужно перевести"""
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                self._extract_translatable_strings(value, result, new_path)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                self._extract_translatable_strings(item, result, new_path)

        elif isinstance(data, str) and self._should_translate(data):
            result[path] = data

    def _apply_translations(self, data, translations):
        """Применяет переводы к данным"""
        if isinstance(data, dict):
            return {k: self._apply_translations(v, translations) for k, v in data.items()}

        elif isinstance(data, list):
            return [self._apply_translations(item, translations) for item in data]

        elif isinstance(data, str) and self._should_translate(data):
            return translations.get(data, data)

        return data

    def _should_translate(self, text):
        """Определяет, нужно ли переводить текст"""
        if not isinstance(text, str) or not text.strip():
            return False

        EXCLUDED_KEYWORDS = getattr(settings, 'TRANSLATION_EXCLUDED_KEYWORDS', ['url', 'slug', 'id', 'price', 'year', 'latitude', 'longitude', 'rating', 'email', 'phone', 'http://', 'https://'])

        if text.startswith(('http://', 'https://')) or text.strip().isdigit():
            return False

        return not any(keyword in text.lower() for keyword in EXCLUDED_KEYWORDS)

    def _translate_strings(self, strings_to_translate, target_language):
        """Переводит строки по одной и кеширует результат"""
        translated_strings = {}

        for text in strings_to_translate.values():
            if text is None:  # Пропускаем None
                continue

            cache_key = f"trans_{hashlib.md5((text + target_language).encode()).hexdigest()}"
            cached_translation = cache.get(cache_key)

            if cached_translation:
                translated_strings[text] = cached_translation
            else:
                try:
                    translated_text = translate(text, target_language)
                    if not translated_text.strip():
                        logger.warning(f"Пустой перевод для: '{text}'")
                        translated_text = text

                    translated_strings[text] = translated_text
                    cache.set(cache_key, translated_text, self.CACHE_TIMEOUT)
                except Exception as e:
                    logger.error(f"Ошибка перевода '{text}': {str(e)}")
                    translated_strings[text] = text

        return translated_strings
