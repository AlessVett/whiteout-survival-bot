import json
import os
from typing import Dict, Any


class Localization:
    def __init__(self, default_lang: str = "en"):
        self.default_lang = default_lang
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.load_translations()

    def load_translations(self):
        locales_dir = os.path.dirname(os.path.abspath(__file__))
        for filename in os.listdir(locales_dir):
            if filename.endswith('.json'):
                lang_code = filename.replace('.json', '')
                with open(os.path.join(locales_dir, filename), 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)

    def get(self, key: str, lang: str = None, **kwargs) -> str:
        if lang is None:
            lang = self.default_lang

        # Supporto per chiavi annidate usando la notazione punto
        keys = key.split('.')
        translation = self.translations.get(lang, {})
        
        for k in keys:
            if isinstance(translation, dict):
                translation = translation.get(k)
            else:
                translation = None
                break
        
        # Se non trovato nella lingua richiesta, prova con quella di default
        if translation is None:
            translation = self.translations.get(self.default_lang, {})
            for k in keys:
                if isinstance(translation, dict):
                    translation = translation.get(k)
                else:
                    translation = key  # Ritorna la chiave se non trova nulla
                    break

        if kwargs and isinstance(translation, str):
            return translation.format(**kwargs)
        return translation if translation is not None else key


_instance = None


def get_localization() -> Localization:
    global _instance
    if _instance is None:
        _instance = Localization()
    return _instance


def t(key: str, lang: str = None, **kwargs) -> str:
    return get_localization().get(key, lang, **kwargs)
