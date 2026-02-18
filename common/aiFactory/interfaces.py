"""
AI API测试器接口定义
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class AIProviderInterface(ABC):
    """AI提供者接口"""
    
    @abstractmethod
    def list_models(self, verbose: bool = True) -> List[Any]:
        """列出可用模型"""
        pass
    
    @abstractmethod
    def show_model(self, model_name: str = None, verbose: bool = True) -> Dict[str, Any]:
        """显示模型详情"""
        pass
    
    @abstractmethod
    def chat_completion(self, model_name: str = None, prompt: str = None,
                       temperature: float = 0.7, max_length: int = 500) -> Dict[str, Any]:
        """聊天完成"""
        pass
    
    @abstractmethod
    def stream_chat(self, model_name: str = None, prompt: str = None,
                   temperature: float = 0.7) -> str:
        """流式聊天"""
        pass
    
    @abstractmethod
    def generate_text(self, model_name: str = None, prompt: str = None,
                     temperature: float = 0.7, max_length: int = 500) -> Dict[str, Any]:
        """文本生成"""
        pass
    
    @abstractmethod
    def create_embeddings(self, model_name: str = None, text: str = None) -> Dict[str, Any]:
        """创建嵌入向量"""
        pass
    
    @abstractmethod
    def extract_image_text(self, image_path: str, model_name: str = None,
                          temperature: float = 0.1, detail_level: str = 'normal') -> Dict[str, Any]:
        """从图像提取文本（OCR）"""
        pass
    
    @abstractmethod
    def image_to_markdown(self, image_path: str, model_name: str = None,
                         temperature: float = 0.3, include_metadata: bool = True) -> Dict[str, Any]:
        """图像转Markdown"""
        pass
    
    @abstractmethod
    def describe_image(self, image_path: str, model_name: str = None,
                      detail_level: str = "detailed") -> Dict[str, Any]:
        """描述图像内容"""
        pass
    
    @abstractmethod
    def analyze_chart(self, image_path: str, model_name: str = None) -> Dict[str, Any]:
        """分析图表"""
        pass
    
    @abstractmethod
    def check_health(self) -> bool:
        """检查服务健康状态"""
        pass