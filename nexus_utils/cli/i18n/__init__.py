"""
Internationalization (i18n) module for Nexus-AI CLI

Provides a simple, maintainable way to support multiple languages.
All user-facing strings are centralized here to ensure consistency
between language versions.

Usage:
    from .i18n import t, set_language
    
    # Set language (default is 'en')
    set_language('zh')
    
    # Get translated string
    print(t('common.success'))  # Output: 成功
    print(t('init.creating_table', name='nexus_agents'))  # Output: 创建表: nexus_agents
"""

from .messages import get_message, set_language, get_current_language

# Shorthand for get_message
t = get_message

__all__ = ['t', 'get_message', 'set_language', 'get_current_language']
