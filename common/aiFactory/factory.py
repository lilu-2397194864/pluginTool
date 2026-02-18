"""
AI提供者工厂类
"""

from enum import Enum
from typing import Union

from .providerQwen import QwenAPITester
from .providerOllama import OllamaAPITester
from .interfaces import AIProviderInterface


class AIProviderType(Enum):
    """AI提供者类型枚举"""
    QWEN = "qwen"
    OLLAMA = "ollama"


class AIProviderFactory:
    """AI提供者工厂类"""
    
    @staticmethod
    def create_provider(provider_type: Union[AIProviderType, str], **kwargs) -> AIProviderInterface:
        """
        创建AI提供者实例
        
        Args:
            provider_type: 提供者类型
            **kwargs: 提供者初始化参数
            
        Returns:
            AIProviderInterface: AI提供者实例
        """
        if isinstance(provider_type, str):
            provider_type = AIProviderType(provider_type.lower())
        
        if provider_type == AIProviderType.QWEN:
            api_key = kwargs.get('api_key')
            return QwenAPITester(api_key=api_key)
        
        elif provider_type == AIProviderType.OLLAMA:
            base_url = kwargs.get('base_url', "http://localhost:11434")
            return OllamaAPITester(base_url=base_url)
        
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")