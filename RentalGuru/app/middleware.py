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

        query_language = request.GET.get('lang')

        if not query_language:
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_language = getattr(request.user, 'language', None)
                target_language = getattr(user_language, 'code',
                                          settings.TRANSLATION_DEFAULT_LANGUAGE) if user_language else settings.TRANSLATION_DEFAULT_LANGUAGE
            else:
                target_language = settings.TRANSLATION_DEFAULT_LANGUAGE
        else:
            target_language = query_language

        if not target_language or target_language == settings.TRANSLATION_DEFAULT_LANGUAGE:
            return response

        if 'application/json' in response.get('Content-Type', ''):
            try:
                data = json.loads(response.content.decode('utf-8'))
                strings_to_translate = {}

                self._extract_translatable_strings(data, strings_to_translate)

                if strings_to_translate:

                    path_to_text = {path: text for path, text in strings_to_translate.items()}

                    translated_strings = self._translate_strings(path_to_text.values(), target_language)

                    translated_data = self._apply_translations_by_path(data, path_to_text, translated_strings)
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

    def _apply_translations_by_path(self, data, path_to_text, translations):
        """Применяет переводы к данным по указанным путям"""

        result = data
        for path, text in path_to_text.items():
            if text in translations:

                components = self._parse_path(path)

                self._set_value_by_path(result, components, translations[text])

        return result

    def _parse_path(self, path):
        """Разбивает путь на компоненты"""
        components = []
        current = ""
        i = 0

        while i < len(path):
            if path[i] == '.':
                if current:
                    components.append(current)
                    current = ""
            elif path[i] == '[':
                if current:
                    components.append(current)
                    current = ""
                i += 1
                index = ""
                while i < len(path) and path[i] != ']':
                    index += path[i]
                    i += 1
                components.append(int(index))
            else:
                current += path[i]
            i += 1

        if current:
            components.append(current)

        return components

    def _set_value_by_path(self, data, components, value):
        """Устанавливает значение по пути"""
        if not components:
            return

        current = data
        for i, component in enumerate(components[:-1]):
            if isinstance(component, int):
                if i < len(components) - 1 and isinstance(components[i + 1], int):
                    if isinstance(current, list) and component < len(current):
                        current = current[component]
                    else:
                        return
                else:
                    if isinstance(current, list) and component < len(current):
                        current = current[component]
                    else:
                        return
            else:
                if isinstance(current, dict) and component in current:
                    current = current[component]
                else:
                    return

        last_component = components[-1]
        if isinstance(last_component, int):
            if isinstance(current, list) and last_component < len(current):
                current[last_component] = value
        else:
            if isinstance(current, dict) and last_component in current:
                current[last_component] = value

    def _should_translate(self, text):
        """Определяет, нужно ли переводить текст"""
        if not isinstance(text, str) or not text.strip():
            return False

        EXCLUDED_KEYWORDS = getattr(settings, 'TRANSLATION_EXCLUDED_KEYWORDS',
                                    ['code', 'url', 'slug', 'id', 'price', 'year', 'latitude', 'longitude', 'rating',
                                     'email', 'phone', 'http://', 'https://'])

        if text.startswith(('http://', 'https://')) or text.strip().isdigit():
            return False

        return not any(keyword in text.lower() for keyword in EXCLUDED_KEYWORDS)

    def _translate_strings(self, strings_to_translate, target_language):
        """Переводит строки и кеширует результат"""
        translated_strings = {}
        unique_strings = set(strings_to_translate)

        for text in unique_strings:
            if text is None:
                continue

            cache_key = f"trans_{target_language}_{hashlib.md5(text.encode()).hexdigest()}"
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