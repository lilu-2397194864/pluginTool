"""
AI API测试器的工厂模式实现
"""

__version__ = "1.0.0"
__author__ = "AI Tester"

from .factory import AIProviderFactory
from .providerQwen import QwenAPITester
from .providerOllama import OllamaAPITester
from .interfaces import AIProviderInterface

__all__ = [
    'AIProviderFactory',
    'QwenAPITester',
    'OllamaAPITester',
    'AIProviderInterface'
]