import json
import logging
import hashlib
import concurrent.futures
from RentalGuru import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from googletrans import Translator, LANGUAGES

logger = logging.getLogger(__name__)

class TranslationMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.translator = Translator()
        self.CACHE_TIMEOUT = getattr(settings, 'TRANSLATION_CACHE_TIMEOUT', 60 * 60 * 24)
        self.MAX_WORKERS = getattr(settings, 'TRANSLATION_MAX_WORKERS', 4)

    def process_response(self, request, response):
        if not getattr(settings, 'TRANSLATION_ENABLED', True):
            return response

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response

        user_language = getattr(request.user, 'language', None)
        user_language = getattr(user_language, 'code', settings.TRANSLATION_DEFAULT_LANGUAGE) if user_language else settings.TRANSLATION_DEFAULT_LANGUAGE

        if not user_language or user_language == settings.TRANSLATION_DEFAULT_LANGUAGE:
            return response

        if user_language not in LANGUAGES:
            logger.warning(f"Язык {user_language} не поддерживается Google Translate")
            return response

        if 'application/json' in response.get('Content-Type', ''):
            try:
                data = json.loads(response.content.decode('utf-8'))
                strings_to_translate = {}

                self._extract_translatable_strings(data, strings_to_translate)

                if strings_to_translate:
                    translated_strings = self._translate_strings_parallel(strings_to_translate, user_language)
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

    def _translate_strings_parallel(self, strings_to_translate, target_language):
        """Переводит строки параллельно, используя ThreadPoolExecutor"""
        unique_strings = {text: text for path, text in strings_to_translate.items()}
        cached_translations = {}
        strings_to_request = []

        for text in unique_strings.keys():
            if text is None:  # Фильтруем None
                continue

            cache_key = f"trans_{hashlib.md5((text + target_language).encode()).hexdigest()}"
            cached = cache.get(cache_key)

            if cached:
                cached_translations[text] = cached
            else:
                strings_to_request.append(text)

        if strings_to_request:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                future_to_batch = {executor.submit(self._translate_batch, batch, target_language): batch for batch in [strings_to_request]}
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch = future_to_batch[future]
                    try:
                        result = future.result()
                        for original, translated in result.items():
                            if translated is None or translated.strip() == "":
                                logger.warning(f"Пустой перевод для '{original}'")
                                translated = original

                            cached_translations[original] = translated
                            cache_key = f"trans_{hashlib.md5((original + target_language).encode()).hexdigest()}"
                            cache.set(cache_key, translated, self.CACHE_TIMEOUT)
                    except Exception as e:
                        logger.error(f"Ошибка при переводе батча: {str(e)}")

        return {text: cached_translations.get(text, text) for text in unique_strings.keys()}

    def _translate_batch(self, texts, target_language):
        """Переводит пакет строк за один запрос к API"""
        result = {}

        try:
            translated = self.translator.translate(texts, dest=target_language)

            if not isinstance(translated, list):
                translated = [translated]

            if len(translated) != len(texts):
                logger.warning(f"Некорректный размер ответа от Google Translate: {len(translated)} вместо {len(texts)}")
                return {text: text for text in texts}

            for i, trans in enumerate(translated):
                if hasattr(trans, 'text') and trans.text:
                    result[texts[i]] = trans.text
                else:
                    result[texts[i]] = texts[i]

        except Exception as e:
            logger.error(f"Ошибка batch-перевода: {str(e)}")
            return {text: text for text in texts}

        return result
