"""
Translation loader for Hermes Agent CLI.
Loads translations based on user's language preference.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default language
DEFAULT_LANG = "en"

# Current language (can be overridden by config or env var)
_current_lang: Optional[str] = None
_translations_cache: Dict[str, Dict[str, Any]] = {}


def get_language() -> str:
    """Get current language code.
    
    Priority:
    1. HERMES_LANGUAGE env var
    2. Config file (display.language)
    3. System locale
    4. Default (en)
    """
    global _current_lang
    
    if _current_lang is not None:
        return _current_lang
    
    # Check environment variable
    env_lang = os.getenv("HERMES_LANGUAGE")
    if env_lang:
        _current_lang = env_lang[:2].lower()
        return _current_lang
    
    # TODO: Check config file when config integration is added
    # from hermes_cli.config import load_config
    # config = load_config()
    # lang = config.get("display", {}).get("language")
    
    # Check system locale
    system_lang = os.getenv("LANG", "").lower()
    if system_lang.startswith("ru"):
        _current_lang = "ru"
        return "ru"
    
    # Default to English
    _current_lang = DEFAULT_LANG
    return DEFAULT_LANG


def set_language(lang: str) -> None:
    """Set the current language."""
    global _current_lang
    _current_lang = lang[:2].lower()
    logger.info(f"Language set to: {_current_lang}")


def load_translations(lang: Optional[str] = None) -> Dict[str, Any]:
    """Load translations for the specified language.
    
    Args:
        lang: Language code (e.g., 'ru', 'en'). Defaults to current language.
        
    Returns:
        Dictionary with all translation strings.
    """
    if lang is None:
        lang = get_language()
    
    # Return cached translations if available
    if lang in _translations_cache:
        return _translations_cache[lang]
    
    # English is the default (no translation needed)
    if lang == DEFAULT_LANG:
        _translations_cache[lang] = {}
        return {}
    
    # Try to load translations module
    try:
        module_name = f"hermes_cli.translations.{lang}"
        module = __import__(module_name, fromlist=[""])
        translations = {}
        
        # Extract all uppercase constants from the module
        for attr_name in dir(module):
            attr_value = getattr(module, attr_name)
            if attr_name.isupper() and isinstance(attr_value, dict):
                translations[attr_name] = attr_value
        
        _translations_cache[lang] = translations
        logger.debug(f"Loaded translations for: {lang}")
        return translations
        
    except ImportError:
        logger.warning(f"No translations available for: {lang}")
        _translations_cache[lang] = {}
        return {}


def translate(key: str, default: Optional[str] = None, context: Optional[str] = None) -> str:
    """Translate a key to the current language.
    
    Args:
        key: Translation key (e.g., 'welcome', 'BANNER.welcome')
        default: Default value if translation not found
        context: Optional context/category (e.g., 'BANNER', 'COMMANDS')
        
    Returns:
        Translated string or default/key if not found
    """
    lang = get_language()
    
    # Return key as-is for English
    if lang == DEFAULT_LANG:
        return default or key
    
    translations = load_translations(lang)
    
    # Support dotted notation: 'BANNER.welcome'
    if "." in key:
        context, key = key.split(".", 1)
    
    if context:
        context_dict = translations.get(context, {})
        value = context_dict.get(key, default)
    else:
        # Search across all contexts
        value = default
        for context_dict in translations.values():
            if key in context_dict:
                value = context_dict[key]
                break
    
    return value if value is not None else key


def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """Shorthand for translate() with optional format arguments.
    
    Args:
        key: Translation key
        default: Default value if translation not found
        **kwargs: Format arguments for .format()
        
    Returns:
        Formatted translated string
        
    Example:
        t('BANNER.update_available', count=5)
    """
    text = translate(key, default)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def is_russian() -> bool:
    """Check if current language is Russian."""
    return get_language() == "ru"


def is_english() -> bool:
    """Check if current language is English."""
    return get_language() == DEFAULT_LANG


# Initialize on import
get_language()
