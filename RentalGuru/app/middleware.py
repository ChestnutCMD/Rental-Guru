import json
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from googletrans import Translator


class TranslationMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if not getattr(settings, 'TRANSLATION_ENABLED', True):
            return response

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response

        user_language = getattr(request.user.language, 'code', settings.TRANSLATION_DEFAULT_LANGUAGE)

        if not user_language or user_language == settings.TRANSLATION_DEFAULT_LANGUAGE:
            return response

        translator = Translator()

        if 'application/json' in response['Content-Type']:
            try:
                data = json.loads(response.content.decode('utf-8'))
                translated_data = self.translate_data(data, translator, user_language)
                response.content = json.dumps(translated_data, ensure_ascii=False).encode('utf-8')
            except Exception as e:
                print(f"Ошибка перевода: {e}")

        return response

    def translate_data(self, data, translator, target_language):
        """ Рекурсивно переводит строки в JSON-ответе """
        if isinstance(data, str):
            return translator.translate(data, dest=target_language).text
        elif isinstance(data, list):
            return [self.translate_data(item, translator, target_language) for item in data]
        elif isinstance(data, dict):
            return {key: self.translate_data(value, translator, target_language) for key, value in data.items()}
        return data
