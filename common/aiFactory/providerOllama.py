"""
OllamaAPITester 测试器的具体实现类
"""

import base64
import json
from pathlib import Path
import requests
import logging
from typing import Dict, Any, List
import ollama
from common.ieltsLog import Logger

from .interfaces import AIProviderInterface

class OllamaAPITester(AIProviderInterface):
    """Ollama API测试器"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """初始化Ollama API测试器"""
        self.logger = Logger('OLLAMA_API')
        self.base_url = base_url
        self.client = ollama.Client(host=base_url)
        
        self.vision_keywords = ['llava', 'bakllava', 'vision', 'moondream', 'clip', 'ocr']
        self.chat_keywords = ['llama', 'mistral', 'gemma', 'qwen', 'phi', 'code', 'chat']
        self.embedding_keywords = ['nomic', 'bge', 'all-minilm', 'embed', 'mxbai']
        
        self.default_temperature = 0.7
        self.default_max_length = 500
        self.default_vision_model = "llava"
        self.default_chat_model = "llama3"
        self.default_embedding_model = "nomic-embed-text"
        
        self.ocr_detail_levels = {
            'simple': 'Extract the text in the image.',
            'normal': '请识别这张图片中的所有文本，准确提取并返回。如果图片中没有文本，请说明。',
            'detailed': """请仔细识别这张图片中的所有文本内容，并准确提取出来。
要求：
1. 提取所有可见的文本，包括标题、正文、标注等
2. 保持原文的格式、顺序和布局
3. 如果是多列或特殊布局，请说明文本排列方式
4. 如果是手写体，请尽力识别并标注为手写
5. 区分不同字体大小和样式
            
请直接输出识别到的文本，不要添加其他内容。"""
        }

        self.image_description_levels = {
            "brief": "请用一两句话简要描述这张图片的内容。",
            "normal": "请详细描述这张图片的内容，包括主要对象、场景、颜色和布局。",
            "detailed": """请非常详细地描述这张图片，包括：
    1. 主要对象和背景
    2. 颜色、光线和氛围
    3. 可能的场景或情境
    4. 文本内容（如果有）
    5. 整体印象和感受
            
    请用结构化的方式描述。"""
        }

        self.chart_analysis_prompt = """请分析这张图表或示意图，并提供以下信息：
1. 图表类型（柱状图、折线图、饼图、散点图等）
2. 图表标题和坐标轴标签（如果可读）
3. 主要数据趋势、模式或发现
4. 关键数据点或数值范围（如果可读）
5. 颜色编码和图例说明
6. 主要结论或业务见解

请用结构化的方式呈现分析结果，使用清晰的标题和项目符号。"""

        self.markdown_conversion_prompt = """请分析这张图片并将其内容转换为结构化的 Markdown 格式。
根据图片内容，可能包括：
1. 如果包含文本，请整理成 Markdown 段落
2. 如果包含列表，请使用 Markdown 列表格式
3. 如果包含表格，请使用 Markdown 表格格式
4. 如果包含代码，请使用代码块格式
5. 描述图片中的视觉元素

请直接输出 Markdown 内容，不要添加额外的解释。"""

        self.available_models = self._get_available_models()
    
    def _get_available_models(self):
        """获取可用模型列表"""
        try:
            response = self.client.list()
            models = []
            
            # Handle different response structures
            if hasattr(response, 'models'):
                # Response from ollama library
                for model in response.models:
                    # Create model info dictionary
                    model_data = {
                        'name': getattr(model, 'name', ''),
                        'model': getattr(model, 'model', ''),
                        'modified_at': getattr(model, 'modified_at', ''),
                        'size': getattr(model, 'size', 0),
                        'digest': getattr(model, 'digest', '')
                    }
                    models.append(model_data)
            elif isinstance(response, dict) and 'models' in response:
                # Response from direct API call
                for model_data in response['models']:
                    models.append(model_data)
            else:
                # Try generic handling
                try:
                    if hasattr(response, '__dict__'):
                        # If it's an object, try to convert to dict
                        response_dict = response.__dict__
                        if 'models' in response_dict:
                            for model_data in response_dict['models']:
                                models.append(model_data)
                except:
                    pass
            
            return models
            
        except Exception as e:
            self.logger.context(logging.ERROR, f'Failed to get model list: {str(e)}')
            return []
    
    def _get_model(self, model_name: str = None, model_type: str = None):
        """获取指定模型"""
        if not self.available_models:
            self.logger.context(logging.WARN, 'No available models')
            return None
        
        if model_name:
            # Find specified model
            for model in self.available_models:
                if model['name'] == model_name or model['model'] == model_name:
                    self.logger.context(logging.INFO, f'Using specified model: {model_name}')
                    return model['model']
            
            self.logger.context(logging.WARN, f'Model not found: {model_name}')
            available_names = [m['name'] for m in self.available_models]
            self.logger.context(logging.INFO, f'Available models: {available_names}')
            return None
        
        # If model type specified, find corresponding model
        if model_type:
            if model_type.lower() == 'vision':
                for model in self.available_models:
                    if any(keyword in model['name'].lower() for keyword in self.vision_keywords):
                        self.logger.context(logging.INFO, f'Auto-selected vision model: {model["name"]}')
                        return model['name']
            
            elif model_type.lower() == 'chat':
                for model in self.available_models:
                    if any(keyword in model['name'].lower() for keyword in self.chat_keywords):
                        self.logger.context(logging.INFO, f'Auto-selected chat model: {model["name"]}')
                        return model['name']
            
            elif model_type.lower() == 'embedding':
                for model in self.available_models:
                    if any(keyword in model['name'].lower() for keyword in self.embedding_keywords):
                        self.logger.context(logging.INFO, f'Auto-selected embedding model: {model["name"]}')
                        return model['name']
        
        # Default to first model
        default_model = self.available_models[0]['name'] if self.available_models else self.default_chat_model
        self.logger.context(logging.INFO, f'Using default model: {default_model}')
        return default_model
    
    def _detect_model_type(self, model_name: str):
        """检测模型类型"""
        if not model_name:
            return 'Unknown'
        
        model_name_lower = model_name.lower()
        
        if any(keyword in model_name_lower for keyword in self.vision_keywords):
            return 'Vision'
        elif any(keyword in model_name_lower for keyword in self.chat_keywords):
            return 'Chat'
        elif any(keyword in model_name_lower for keyword in self.embedding_keywords):
            return 'Embedding'
        else:
            return 'General'
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """将图像编码为base64"""
        self.logger.context(logging.DEBUG, f'Start encoding image: {image_path}')
        try:
            with open(image_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            file_size = Path(image_path).stat().st_size
            self.logger.context(logging.INFO, f'Image encoding completed: {image_path}, size: {file_size} bytes')
            return encoded_string
        except Exception as e:
            self.logger.context(logging.ERROR, f'Image encoding failed: {str(e)}')
            raise e
    
    def list_models(self, verbose: bool = True) -> List[Dict[str, Any]]:
        """列出可用模型"""
        self.logger.context(logging.INFO, 'Start testing list local models API')
        
        try:
            self.logger.context(logging.DEBUG, 'Call client.list() method')
            response = self.client.list()
            
            # Re-parse response
            models = []
            if hasattr(response, 'models'):
                for model in response.models:
                    model_data = {
                        'name': getattr(model, 'name', getattr(model, 'model', '')),
                        'model': getattr(model, 'model', ''),
                        'modified_at': getattr(model, 'modified_at', ''),
                        'size': getattr(model, 'size', 0),
                        'digest': getattr(model, 'digest', '')
                    }
                    models.append(model_data)
            elif isinstance(response, dict) and 'models' in response:
                for model_data in response['models']:
                    models.append(model_data)
            else:
                # Try direct access
                try:
                    if hasattr(response, '__dict__'):
                        response_dict = response.__dict__
                        if 'models' in response_dict:
                            for model_data in response_dict['models']:
                                models.append(model_data)
                except Exception as e:
                    self.logger.context(logging.ERROR, f'Failed to parse model data: {str(e)}')
            
            self.available_models = models
            
            model_count = len(models)
            self.logger.context(logging.INFO, f'Successfully obtained {model_count} models')
            
            if verbose and model_count > 0:
                for model in models:
                    model_info = f"Model: {model['name']}"
                    if model.get('size'):
                        # Convert to GB
                        size_gb = model['size'] / (1024**3)
                        model_info += f", Size: {size_gb:.2f}GB"
                    if model.get('modified_at'):
                        model_info += f", Modified: {model['modified_at']}"
                    if model.get('digest'):
                        model_info += f", Digest: {model['digest'][:16]}..."
                    
                    # Mark model type
                    model_type = self._detect_model_type(model['name'])
                    if model_type:
                        model_info += f", Type: {model_type}"
                    
                    self.logger.context(logging.INFO, model_info)
            
            return models
            
        except Exception as e:
            error_msg = f"Failed to list local models: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return []
    
    def show_model(self, model_name: str = None, verbose: bool = True) -> Dict[str, Any]:
        """显示模型详情"""
        self.logger.context(logging.INFO, f'Start testing show model details API')
        
        try:
            # Get model name
            target_model = self._get_model(model_name)
            if not target_model:
                self.logger.context(logging.ERROR, 'Cannot get model name')
                return None
            
            self.logger.context(logging.DEBUG, f'Call client.show("{target_model}")')
            model_info = self.client.show(target_model)
            self.logger.context(logging.INFO, f'Successfully obtained model {target_model} details')
            
            if verbose:
                try:
                    model_details = json.dumps(model_info, indent=2, ensure_ascii=False)
                    self.logger.context(logging.INFO, f'Model details: {model_details}')
                except:
                    self.logger.context(logging.INFO, f'Model info: {model_info}')
            else:
                # Extract key information
                if isinstance(model_info, dict):
                    model_info_dict = model_info.get('model_info', {})
                    self.logger.context(logging.INFO, f'Model architecture: {model_info_dict.get("architecture", "Unknown")}')
                    self.logger.context(logging.INFO, f'Model size: {model_info_dict.get("size", "Unknown")}')
                    self.logger.context(logging.INFO, f'Parameter count: {model_info_dict.get("parameters", "Unknown")}')
                    
                    # Show template information
                    template = model_info.get('template', '')
                    if template:
                        self.logger.context(logging.INFO, f'Template preview: {template[:200]}...')
                else:
                    self.logger.context(logging.INFO, f'Model info type: {type(model_info)}')
                    self.logger.context(logging.INFO, f'Model info: {str(model_info)[:500]}...')
            
            return model_info
            
        except Exception as e:
            error_msg = f"Failed to show model details: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return None
    
    def chat_completion(self, model_name: str = "deepseek-v3.1:671b-cloud", prompt: str = None,
                       temperature: float = 0.7, max_length: int = 500) -> Dict[str, Any]:
        """聊天完成"""
        self.logger.context(logging.INFO, f'Start testing chat completion API')
        
        try:
            # Get model name
            target_model = self._get_model(model_name, 'chat')
            if not target_model:
                self.logger.context(logging.ERROR, f'Cannot get chat model, {model_name}')
                return None
            
            # Set prompt
            if not prompt:
                prompt = '你好，请用中文介绍一下你自己。'
            
            self.logger.context(logging.INFO, f'Using model: {target_model}')
            self.logger.context(logging.INFO, f'Prompt: {prompt}')
            
            # Basic chat
            self.logger.context(logging.DEBUG, 'Testing basic chat function')
            response = self.client.chat(
                model=target_model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'temperature': temperature,
                    'num_predict': max_length
                }
            )
            self.logger.context(logging.INFO, 'Chat completion finished')
            
            chat_response = response['message']['content']
            self.logger.context(logging.INFO, f'Chat response preview: {chat_response[:200]}...')
            
            # Print AI response content
            self.logger.context(logging.INFO, 'AI Response Content:')
            self.logger.context(logging.INFO, '-' * 40)
            self.logger.context(logging.INFO, chat_response)
            self.logger.context(logging.INFO, '-' * 40)
            
            return response
            
        except Exception as e:
            error_msg = f"Chat completion API test failed: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return None
    
    def stream_chat(self, model_name: str = None, prompt: str = None,
                   temperature: float = 0.7) -> str:
        """流式聊天"""
        self.logger.context(logging.INFO, 'Start testing streaming chat API')
        
        try:
            # Get model name
            target_model = self._get_model(model_name, 'chat')
            if not target_model:
                self.logger.context(logging.ERROR, 'Cannot get chat model')
                return None
            
            # Set prompt
            if not prompt:
                prompt = '请用中文列举三个Python的优点。'
            
            self.logger.context(logging.INFO, f'Using model: {target_model}')
            self.logger.context(logging.INFO, f'Prompt: {prompt}')
            
            stream_response = self.client.chat(
                model=target_model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={'temperature': temperature},
                stream=True
            )
            
            self.logger.context(logging.DEBUG, 'Start receiving streaming response')
            full_response = ""
            chunk_count = 0
            
            for chunk in stream_response:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    full_response += content
                    chunk_count += 1
                    
                    # Record progress every 5 chunks
                    if chunk_count % 5 == 0:
                        self.logger.context(logging.DEBUG, f'Received {chunk_count} data chunks')
            
            self.logger.context(logging.INFO, f'Streaming chat completed, total {chunk_count} data chunks received')
            self.logger.context(logging.INFO, f'Full response preview: {full_response[:200]}...')
            
            # Print AI response content
            self.logger.context(logging.INFO, 'AI Response Content:')
            self.logger.context(logging.INFO, '-' * 40)
            self.logger.context(logging.INFO, full_response)
            self.logger.context(logging.INFO, '-' * 40)
            
            return full_response
            
        except Exception as e:
            error_msg = f"Streaming chat API test failed: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return None
    
    def generate_text(self, model_name: str = None, prompt: str = None,
                     temperature: float = 0.7, max_length: int = 500) -> Dict[str, Any]:
        """文本生成"""
        self.logger.context(logging.INFO, 'Start testing text generation API')
        
        try:
            # Get model name
            target_model = self._get_model(model_name, 'chat')
            if not target_model:
                self.logger.context(logging.ERROR, 'Cannot get generation model')
                return None
            
            # Set prompt
            if not prompt:
                prompt = '请用中文写一个简短的 Python 函数来计算斐波那契数列。'
            
            self.logger.context(logging.INFO, f'Using model: {target_model}')
            self.logger.context(logging.INFO, f'Prompt: {prompt}')
            
            # Basic text generation
            self.logger.context(logging.DEBUG, 'Testing basic text generation')
            response = self.client.generate(
                model=target_model,
                prompt=prompt,
                options={
                    'temperature': temperature,
                    'num_predict': max_length
                }
            )
            self.logger.context(logging.INFO, 'Text generation completed')
            
            generated_text = response['response']
            self.logger.context(logging.INFO, f'Generated text preview: {generated_text[:200]}...')
            
            # Print AI response content
            self.logger.context(logging.INFO, 'AI Response Content:')
            self.logger.context(logging.INFO, '-' * 40)
            self.logger.context(logging.INFO, generated_text)
            self.logger.context(logging.INFO, '-' * 40)
            
            return response
            
        except Exception as e:
            error_msg = f"Text generation API test failed: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return None
    
    def create_embeddings(self, model_name: str = None, text: str = None) -> Dict[str, Any]:
        """创建嵌入向量"""
        self.logger.context(logging.INFO, 'Start testing embedding generation API')
        
        try:
            # Get model name
            target_model = self._get_model(model_name, 'embedding')
            if not target_model:
                self.logger.context(logging.WARN, 'No specialized embedding model found, trying general model')
                target_model = self._get_model(model_name)
                if not target_model:
                    self.logger.context(logging.ERROR, 'Cannot get model')
                    return None
            
            # Set text
            if not text:
                text = '这是一个测试句子，用于生成嵌入向量。'
            
            self.logger.context(logging.INFO, f'Using model: {target_model}')
            self.logger.context(logging.INFO, f'Input text: {text}')
            
            response = self.client.embeddings(
                model=target_model,
                prompt=text
            )
            
            embedding = response['embedding']
            vector_length = len(embedding)
            self.logger.context(logging.INFO, f'Successfully generated embedding, length: {vector_length}')
            
            if vector_length > 0:
                first_five = embedding[:5]
                last_five = embedding[-5:] if vector_length > 5 else embedding
                self.logger.context(logging.INFO, f'First 5 values: {first_five}')
                self.logger.context(logging.INFO, f'Last 5 values: {last_five}')
            
            return response
            
        except Exception as e:
            error_msg = f"Embedding generation API test failed: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return None
    
    def extract_image_text(self, image_path: str, model_name: str = 'deepseek-ocr:3b',
                          temperature: float = 0.1, detail_level: str = 'normal') -> Dict[str, Any]:
        """从图像提取文本（OCR）"""
        self.logger.context(logging.INFO, f'Start testing OCR text extraction from image, path: {image_path}')
        
        if not image_path:
            self.logger.context(logging.WARN, 'No image path provided')
            return None
        
        if not Path(image_path).exists():
            self.logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            self.logger.context(logging.INFO, f'Processing image: {image_path}')
            
            # 检查图片格式
            image_suffix = Path(image_path).suffix.lower()
            self.logger.context(logging.DEBUG, f'Image format: {image_suffix}')
            
            image_base64 = self.encode_image_to_base64(image_path)
            
            # 获取视觉模型
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                self.logger.context(logging.WARN, 'No vision model found')
                self.logger.context(logging.INFO, 'Please pull vision model first: ollama pull llava or ollama pull deepseek-ocr')
                return None
            
            self.logger.context(logging.INFO, f'Using vision model: {target_model}')
            
            # 根据详细级别设置提示词
            prompt = self.ocr_detail_levels.get(detail_level, self.ocr_detail_levels['normal'])
            self.logger.context(logging.DEBUG, f'Using prompt for detail level "{detail_level}": {prompt[:100]}...')
            
            messages = [{
                'role': 'user',
                'content': prompt,
                'images': [image_base64]
            }]
            
            self.logger.context(logging.INFO, f'Starting OCR extraction, detail level: {detail_level}')
            
            # 尝试使用 generate 方法
            self.logger.context(logging.INFO, 'Trying generate method as alternative...')
            response = self.client.generate(
                model=target_model,
                prompt=prompt,
                images=[image_base64],
                options={'temperature': temperature}
            )
            # 转换响应格式
            response = {'message': {'content': response.get('response', '')}}

            self.logger.context(logging.INFO, 'OCR extraction completed')
            
            # 检查响应结构
            if not response or 'message' not in response:
                self.logger.context(logging.WARN, f'Unexpected response structure: {response}')
                ocr_result = ""
            else:
                ocr_result = response['message'].get('content', '')
            
            result_length = len(ocr_result)
            self.logger.context(logging.INFO, f'OCR result length: {result_length} characters')
            
            if result_length > 0:
                self.logger.context(logging.INFO, f'OCR result preview: {ocr_result[:200]}...')
                
                # Print AI response content
                self.logger.context(logging.INFO, 'AI Response Content:')
                self.logger.context(logging.INFO, '-' * 40)
                self.logger.context(logging.INFO, ocr_result)
                self.logger.context(logging.INFO, '-' * 40)
            else:
                self.logger.context(logging.ERROR, 'OCR result fail')
                return None
            
            # 保存结果到文件
            output_file = f"ocr_result_{Path(image_path).stem}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# OCR Extraction Result\n\n")
                f.write(f"**Source Image**: {image_path}\n")
                f.write(f"**Model**: {target_model}\n")
                f.write(f"**Detail Level**: {detail_level}\n")
                f.write(f"**Result Length**: {result_length} characters\n")
                f.write(f"**Extraction Time**: {response.get('created_at', 'Unknown')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(ocr_result)
            
            self.logger.context(logging.INFO, f'OCR result saved to: {output_file}')
            
            return {
                'text': ocr_result,
                'model': target_model,
                'file': output_file,
                'length': result_length,
                'success': result_length > 0
            }
            
        except Exception as e:
            error_msg = f"OCR test failed: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return None
    
    def image_to_markdown(self, image_path: str, model_name: str = None,
                         temperature: float = 0.3, include_metadata: bool = True) -> Dict[str, Any]:
        """图像转Markdown"""
        self.logger.context(logging.INFO, f'Start testing image to Markdown conversion, path: {image_path}')
        
        if not image_path:
            self.logger.context(logging.WARN, 'No image path provided')
            return None
        
        if not Path(image_path).exists():
            self.logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            self.logger.context(logging.INFO, f'Processing image: {image_path}')
            image_base64 = self.encode_image_to_base64(image_path)
            
            # 获取视觉模型
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                self.logger.context(logging.WARN, 'No vision model found')
                self.logger.context(logging.INFO, 'Available vision models:')
                vision_models = [m['name'] for m in self.available_models 
                                if any(k in m['name'].lower() for k in self.vision_keywords)]
                for vm in vision_models:
                    self.logger.context(logging.INFO, f'  - {vm}')
                return None
            
            self.logger.context(logging.INFO, f'Using vision model: {target_model}')
            
            # 使用宏定义中的提示词
            prompt = self.markdown_conversion_prompt
            
            messages = [{
                'role': 'user',
                'content': prompt,
                'images': [image_base64]
            }]
            
            self.logger.context(logging.INFO, 'Starting Markdown conversion')
            
            try:
                response = self.client.chat(
                    model=target_model,
                    messages=messages,
                    options={'temperature': temperature}
                )
            except Exception as e:
                self.logger.context(logging.ERROR, f'Chat API call failed: {str(e)}')
                # 尝试使用 generate 方法
                self.logger.context(logging.INFO, 'Trying generate method as alternative...')
                try:
                    response = self.client.generate(
                        model=target_model,
                        prompt=prompt,
                        images=[image_base64],
                        options={'temperature': temperature}
                    )
                    # 转换响应格式
                    response = {'message': {'content': response.get('response', '')}}
                except Exception as gen_e:
                    self.logger.context(logging.ERROR, f'Generate method also failed: {str(gen_e)}')
                    return None
            
            self.logger.context(logging.INFO, 'Markdown conversion completed')
            
            # 检查响应结构
            if not response or 'message' not in response:
                self.logger.context(logging.WARN, f'Unexpected response structure: {response}')
                markdown_content = ""
            else:
                markdown_content = response['message'].get('content', '')
            
            content_length = len(markdown_content)
            self.logger.context(logging.INFO, f'Markdown content length: {content_length} characters')
            
            if content_length > 0:
                self.logger.context(logging.INFO, f'Markdown preview: {markdown_content[:200]}...')
                
                # Print AI response content
                self.logger.context(logging.INFO, 'AI Response Content:')
                self.logger.context(logging.INFO, '-' * 40)
                self.logger.context(logging.INFO, markdown_content)
                self.logger.context(logging.INFO, '-' * 40)
            else:
                self.logger.context(logging.WARN, 'Markdown conversion result is empty')
                
                # 尝试简单的描述
                self.logger.context(logging.INFO, 'Trying simple image description...')
                simple_prompt = "Describe this image in detail."
                try:
                    simple_response = self.client.chat(
                        model=target_model,
                        messages=[{
                            'role': 'user',
                            'content': simple_prompt,
                            'images': [image_base64]
                        }],
                        options={'temperature': temperature}
                    )
                    simple_result = simple_response['message'].get('content', '')
                    if simple_result and len(simple_result) > 0:
                        self.logger.context(logging.INFO, f'Simple description result: {simple_result[:200]}...')
                        markdown_content = f"# Image Description\n\n{simple_result}"
                        content_length = len(markdown_content)

                except Exception as e:
                    error_msg = f"OCR test failed: {str(e)}"
                    self.logger.context(logging.ERROR, error_msg)
                    return None

            
            # 保存结果到文件
            output_file = f"markdown_result_{Path(image_path).stem}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                if include_metadata:
                    f.write(f"# Image to Markdown Result\n\n")
                    f.write(f"**Source Image**: {image_path}\n\n")
                    f.write(f"**Conversion Model**: {target_model}\n\n")
                    f.write(f"**Content Length**: {content_length} characters\n\n")
                    f.write(f"**Conversion Time**: {response.get('created_at', 'Unknown')}\n\n")
                    f.write("## Content\n\n")
                f.write(markdown_content)
            
            self.logger.context(logging.INFO, f'Markdown result saved to: {output_file}')
            
            return {
                'markdown': markdown_content,
                'model': target_model,
                'file': output_file,
                'length': content_length,
                'success': content_length > 0
            }
            
        except Exception as e:
            error_msg = f"Markdown conversion test failed: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return None
    
    def describe_image(self, image_path: str, model_name: str = None,
                      detail_level: str = "detailed") -> Dict[str, Any]:
        """描述图像内容"""
        self.logger.context(logging.INFO, f'Start describing image content: {image_path}')
        
        if not image_path or not Path(image_path).exists():
            self.logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            image_base64 = self.encode_image_to_base64(image_path)
            
            # Get vision model
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                self.logger.context(logging.WARN, 'No vision model found')
                return None
            
            # Use macro-defined detail level prompts
            prompt = self.image_description_levels.get(detail_level, self.image_description_levels["normal"])
            
            self.logger.context(logging.DEBUG, f'Calling chat API for image description, detail level: {detail_level}')
            response = self.client.chat(
                model=target_model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_base64]
                }],
                options={'temperature': 0.5}
            )
            
            description = response['message']['content']
            description_length = len(description)
            self.logger.context(logging.INFO, f'Image description completed, description length: {description_length} characters')
            
            # Print AI response content
            self.logger.context(logging.INFO, 'AI Response Content:')
            self.logger.context(logging.INFO, '-' * 40)
            self.logger.context(logging.INFO, description)
            self.logger.context(logging.INFO, '-' * 40)
            
            return {
                'description': description,
                'model': target_model,
                'detail_level': detail_level,
                'length': description_length
            }
            
        except Exception as e:
            self.logger.context(logging.ERROR, f'Image description failed: {str(e)}')
            return None
    
    def analyze_chart(self, image_path: str, model_name: str = None) -> Dict[str, Any]:
        """分析图表"""
        self.logger.context(logging.INFO, f'Start analyzing chart: {image_path}')
        
        if not image_path or not Path(image_path).exists():
            self.logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            image_base64 = self.encode_image_to_base64(image_path)
            
            # Get vision model
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                self.logger.context(logging.WARN, 'No vision model found')
                return None
            
            # Use macro-defined chart analysis prompt
            prompt = self.chart_analysis_prompt
            
            self.logger.context(logging.DEBUG, 'Calling chat API for chart analysis')
            response = self.client.chat(
                model=target_model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_base64]
                }],
                options={'temperature': 0.2}
            )
            
            analysis_result = response['message']['content']
            analysis_length = len(analysis_result)
            self.logger.context(logging.INFO, f'Chart analysis completed, result length: {analysis_length} characters')
            
            # Print AI response content
            self.logger.context(logging.INFO, 'AI Response Content:')
            self.logger.context(logging.INFO, '-' * 40)
            self.logger.context(logging.INFO, analysis_result)
            self.logger.context(logging.INFO, '-' * 40)
            
            # Save analysis result
            output_file = f"chart_analysis_{Path(image_path).stem}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Chart Analysis Result\n\n")
                f.write(f"**Chart File**: {image_path}\n")
                f.write(f"**Analysis Model**: {target_model}\n")
                f.write(f"**Analysis Time**: {response.get('created_at', 'Unknown')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(analysis_result)
            
            self.logger.context(logging.INFO, f'Chart analysis result saved to: {output_file}')
            
            return {
                'analysis': analysis_result,
                'model': target_model,
                'file': output_file,
                'length': analysis_length
            }
            
        except Exception as e:
            self.logger.context(logging.ERROR, f'Chart analysis failed: {str(e)}')
            return None
    
    def check_health(self) -> bool:
        """检查服务健康状态"""
        self.logger.context(logging.INFO, 'Start testing service health check API')
        
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            self.logger.context(logging.INFO, f'Service health check completed, status code: {response.status_code}')
            
            if response.status_code == 200:
                self.logger.context(logging.INFO, 'Ollama service is running normally')
                self.logger.context(logging.INFO, f'Service version: {response.text}')
            else:
                self.logger.context(logging.WARN, f'Ollama service abnormal, status code: {response.status_code}')
            
            return response.status_code == 200
            
        except requests.exceptions.ConnectionError:
            self.logger.context(logging.ERROR, 'Cannot connect to Ollama service, please ensure service is started')
            self.logger.context(logging.INFO, f'Please check if service is running at: {self.base_url}')
            return False
        except Exception as e:
            error_msg = f"Service health check failed: {str(e)}"
            self.logger.context(logging.ERROR, error_msg)
            return False