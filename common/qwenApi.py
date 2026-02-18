import base64
import json
from pathlib import Path
import requests
import logging
from typing import Dict, Any
import dashscope
from dashscope import MultiModalConversation
from http import HTTPStatus

# 使用您提供的日志类
from common.ieltsLog import Logger
# from ieltsLog import Logger
logger = Logger('QWEN_API_TEST')

# ============ 宏定义/常量配置 ============

# 模型类型关键字
VISION_MODEL_KEYWORDS = ['vl', 'vision', 'ocr']
CHAT_MODEL_KEYWORDS = ['qwen', 'chat']
EMBEDDING_MODEL_KEYWORDS = ['text-embedding']

# 默认配置
DEFAULT_QWEN_CHAT_MODEL = "qwen-max"
DEFAULT_QWEN_VISION_MODEL = "qwen-vl-max"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_LENGTH = 500

# OCR详细级别配置
OCR_DETAIL_LEVELS = {
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

# 图片描述详细级别配置
IMAGE_DESCRIPTION_LEVELS = {
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

# 图表分析提示词
CHART_ANALYSIS_PROMPT = """请分析这张图表或示意图，并提供以下信息：
1. 图表类型（柱状图、折线图、饼图、散点图等）
2. 图表标题和坐标轴标签（如果可读）
3. 主要数据趋势、模式或发现
4. 关键数据点或数值范围（如果可读）
5. 颜色编码和图例说明
6. 主要结论或业务见解

请用结构化的方式呈现分析结果，使用清晰的标题和项目符号。"""

# Markdown转换提示词
MARKDOWN_CONVERSION_PROMPT = """请分析这张图片并将其内容转换为结构化的 Markdown 格式。
根据图片内容，可能包括：
1. 如果包含文本，请整理成 Markdown 段落
2. 如果包含列表，请使用 Markdown 列表格式
3. 如果包含表格，请使用 Markdown 表格格式
4. 如果包含代码，请使用代码块格式
5. 描述图片中的视觉元素

请直接输出 Markdown 内容，不要添加额外的解释。"""

# 日志分隔符
LOG_SEPARATOR = "=" * 60
LOG_SECTION_SEPARATOR = "=" * 80

# ============ 模型数据结构 ============

class ModelInfo:
    """Model information class"""
    def __init__(self, model_data: Dict[str, Any]):
        self.name = model_data.get('name', '')
        self.model = model_data.get('model', '')
        self.modified_at = model_data.get('modified_at', '')
        self.size = model_data.get('size', 0)
        self.digest = model_data.get('digest', '')
        
    def __str__(self):
        return f"ModelInfo(name={self.name}, size={self.size})"
    
    def __repr__(self):
        return str(self)

# ============ 类定义 ============

class QwenAPITester:
    def __init__(self, api_key: str = None):
        """Initialize Qwen API tester"""
        logger.context(logging.INFO, f'Initialize Qwen API tester')
        if api_key:
            dashscope.api_key = api_key
        self.available_models = [
            ModelInfo({'name': 'qwen-max', 'model': 'qwen-max'}),
            ModelInfo({'name': 'qwen-plus', 'model': 'qwen-plus'}),
            ModelInfo({'name': 'qwen-turbo', 'model': 'qwen-turbo'}),
            ModelInfo({'name': 'qwen-vl-max', 'model': 'qwen-vl-max'}),
            ModelInfo({'name': 'qwen-vl-plus', 'model': 'qwen-vl-plus'}),
        ]
    
    def _get_model(self, model_name: str = None, model_type: str = None):
        """Get specified model, return first available if not specified"""
        if not self.available_models:
            logger.context(logging.WARN, 'No available models')
            return None
        
        if model_name:
            # Find specified model
            for model in self.available_models:
                if model.model == model_name:
                    logger.context(logging.INFO, f'Using specified model: {model_name}')
                    return model_name
            
            logger.context(logging.WARN, f'Model not found: {model_name}')
            available_names = [m.name for m in self.available_models]
            logger.context(logging.INFO, f'Available models: {available_names}')
            return None
        
        # If model type specified, find corresponding model
        if model_type:
            if model_type.lower() == 'vision':
                for model in self.available_models:
                    if any(keyword in model.name.lower() for keyword in VISION_MODEL_KEYWORDS):
                        logger.context(logging.INFO, f'Auto-selected vision model: {model.name}')
                        return model.name
            
            elif model_type.lower() == 'chat':
                for model in self.available_models:
                    if any(keyword in model.name.lower() for keyword in CHAT_MODEL_KEYWORDS):
                        logger.context(logging.INFO, f'Auto-selected chat model: {model.name}')
                        return model.name
            
            elif model_type.lower() == 'embedding':
                for model in self.available_models:
                    if any(keyword in model.name.lower() for keyword in EMBEDDING_MODEL_KEYWORDS):
                        logger.context(logging.INFO, f'Auto-selected embedding model: {model.name}')
                        return model.name
        
        # Default to first model
        if model_type == 'vision':
            default_model = DEFAULT_QWEN_VISION_MODEL
        else:
            default_model = DEFAULT_QWEN_CHAT_MODEL
        logger.context(logging.INFO, f'Using default model: {default_model}')
        return default_model
    
    def qwen_list_models(self, verbose: bool = True):
        """List all available models"""
        logger.context(logging.INFO, 'Start testing list available models API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test list available models API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            model_count = len(self.available_models)
            logger.context(logging.INFO, f'Successfully obtained {model_count} models')
            
            if verbose and model_count > 0:
                for model in self.available_models:
                    model_info = f"Model: {model.name}"
                    if model.size:
                        # Convert to GB
                        size_gb = model.size / (1024**3)
                        model_info += f", Size: {size_gb:.2f}GB"
                    if model.modified_at:
                        model_info += f", Modified: {model.modified_at}"
                    if model.digest:
                        model_info += f", Digest: {model.digest[:16]}..."
                    
                    # Mark model type
                    model_type = self._detect_model_type(model.name)
                    if model_type:
                        model_info += f", Type: {model_type}"
                    
                    logger.context(logging.INFO, model_info)
            
            logger.context(logging.INFO, '')
            return self.available_models
            
        except Exception as e:
            error_msg = f"Failed to list available models: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            logger.context(logging.DEBUG, f'Full error: {e}', exc_info=True)
            return []
    
    def _detect_model_type(self, model_name: str):
        """Detect model type"""
        if not model_name:
            return 'Unknown'
        
        model_name_lower = model_name.lower()
        
        if any(keyword in model_name_lower for keyword in VISION_MODEL_KEYWORDS):
            return 'Vision'
        elif any(keyword in model_name_lower for keyword in CHAT_MODEL_KEYWORDS):
            return 'Chat'
        elif any(keyword in model_name_lower for keyword in EMBEDDING_MODEL_KEYWORDS):
            return 'Embedding'
        else:
            return 'General'
    
    def qwen_show_model(self, model_name: str = None, verbose: bool = True):
        """Show model details"""
        logger.context(logging.INFO, f'Start testing show model details API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test show model details API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            # Get model name
            target_model = self._get_model(model_name)
            if not target_model:
                logger.context(logging.ERROR, 'Cannot get model name')
                return None
            
            # Mock model details since Qwen API doesn't have a show endpoint
            model_info = {
                'model': target_model,
                'capabilities': 'text generation, conversation',
                'max_tokens': 32768,
                'context_window': 32768,
                'tokenizer': 'Qwen tokenizer',
                'description': f'Details for {target_model} model'
            }
            
            logger.context(logging.INFO, f'Successfully obtained model {target_model} details')
            
            if verbose:
                try:
                    model_details = json.dumps(model_info, indent=2, ensure_ascii=False)
                    logger.context(logging.INFO, f'Model details: {model_details}')
                except:
                    logger.context(logging.INFO, f'Model info: {model_info}')
            else:
                logger.context(logging.INFO, f'Model: {target_model}')
                logger.context(logging.INFO, f'Capabilities: {model_info.get("capabilities", "Unknown")}')
                logger.context(logging.INFO, f'Max tokens: {model_info.get("max_tokens", "Unknown")}')
            
            logger.context(logging.INFO, '')
            return model_info
            
        except Exception as e:
            error_msg = f"Failed to show model details: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return None
    
    def qwen_copy_model(self, source_model: str = None, dest_model: str = None, 
                          source_model_name: str = None):
        """Copy model - Not applicable for Qwen API"""
        logger.context(logging.INFO, f'Start testing copy model API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test copy model API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        logger.context(logging.WARN, 'Copy model operation is not supported by Qwen API')
        logger.context(logging.INFO, '')
        return False
    
    def qwen_delete_model(self, model_name: str):
        """Delete model - Not applicable for Qwen API"""
        logger.context(logging.INFO, f'Start testing delete model API, model: {model_name}')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test delete model API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        logger.context(logging.WARN, 'Delete model operation is not supported by Qwen API')
        logger.context(logging.INFO, '')
        return False
    
    def qwen_chat_completion(self, model_name: str = None, prompt: str = None, 
                              temperature: float = DEFAULT_TEMPERATURE, 
                              max_length: int = DEFAULT_MAX_LENGTH):
        """Test chat completion API"""
        logger.context(logging.INFO, f'Start testing chat completion API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test chat completion API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            # Get model name
            target_model = self._get_model(model_name, 'chat')
            if not target_model:
                logger.context(logging.ERROR, 'Cannot get chat model')
                return None
            
            # Set prompt
            if not prompt:
                prompt = '你好，请用中文介绍一下你自己。'
            
            logger.context(logging.INFO, f'Using model: {target_model}')
            logger.context(logging.INFO, f'Prompt: {prompt}')
            
            # Chat completion using DashScope
            messages = [{'role': 'user', 'content': prompt}]
            
            response = dashscope.Generation.call(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_length,
                result_format='message'
            )
            
            if response.status_code == HTTPStatus.OK:
                chat_response = response.output.choices[0]['message']['content']
                logger.context(logging.INFO, 'Chat completion finished')
                
                logger.context(logging.INFO, f'Chat response preview: {chat_response[:200]}...')
                
                # Print AI response content
                logger.context(logging.INFO, 'AI Response Content:')
                logger.context(logging.INFO, '-' * 40)
                logger.context(logging.INFO, chat_response)
                logger.context(logging.INFO, '-' * 40)
                
                logger.context(logging.INFO, '')
                return {'message': {'content': chat_response}}
            else:
                logger.context(logging.ERROR, f'Chat completion failed: {response.code}, {response.message}')
                return None
                
        except Exception as e:
            error_msg = f"Chat completion API test failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return None
    
    def qwen_stream_chat(self, model_name: str = None, prompt: str = None,
                          temperature: float = DEFAULT_TEMPERATURE):
        """Test streaming chat API"""
        logger.context(logging.INFO, 'Start testing streaming chat API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test streaming chat API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            # Get model name
            target_model = self._get_model(model_name, 'chat')
            if not target_model:
                logger.context(logging.ERROR, 'Cannot get chat model')
                return None
            
            # Set prompt
            if not prompt:
                prompt = '请用中文列举三个Python的优点。'
            
            logger.context(logging.INFO, f'Using model: {target_model}')
            logger.context(logging.INFO, f'Prompt: {prompt}')
            
            messages = [{'role': 'user', 'content': prompt}]
            
            # Streaming chat using DashScope
            responses = dashscope.Generation.call(
                model=target_model,
                messages=messages,
                temperature=temperature,
                result_format='message',
                stream=True,
                output_in_full=True
            )
            
            logger.context(logging.DEBUG, 'Start receiving streaming response')
            full_response = ""
            chunk_count = 0
            
            for response in responses:
                if response.status_code == HTTPStatus.OK:
                    content = response.output.choices[0]['message']['content']
                    if content:
                        full_response = content  # For streaming, update full response
                        chunk_count += 1
                        
                        # Record progress every 5 chunks
                        if chunk_count % 5 == 0:
                            logger.context(logging.DEBUG, f'Received {chunk_count} data chunks')
                else:
                    logger.context(logging.ERROR, f'Streaming response error: {response.code}, {response.message}')
                    break
            
            logger.context(logging.INFO, f'Streaming chat completed, total {chunk_count} data chunks received')
            logger.context(logging.INFO, f'Full response preview: {full_response[:200]}...')
            
            # Print AI response content
            logger.context(logging.INFO, 'AI Response Content:')
            logger.context(logging.INFO, '-' * 40)
            logger.context(logging.INFO, full_response)
            logger.context(logging.INFO, '-' * 40)
            
            logger.context(logging.INFO, '')
            
            return full_response
            
        except Exception as e:
            error_msg = f"Streaming chat API test failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return None
    
    def qwen_generate_text(self, model_name: str = None, prompt: str = None,
                            temperature: float = DEFAULT_TEMPERATURE, 
                            max_length: int = DEFAULT_MAX_LENGTH):
        """Test text generation API"""
        logger.context(logging.INFO, 'Start testing text generation API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test text generation API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            # Get model name
            target_model = self._get_model(model_name, 'chat')
            if not target_model:
                logger.context(logging.ERROR, 'Cannot get generation model')
                return None
            
            # Set prompt
            if not prompt:
                prompt = '请用中文写一个简短的 Python 函数来计算斐波那契数列。'
            
            logger.context(logging.INFO, f'Using model: {target_model}')
            logger.context(logging.INFO, f'Prompt: {prompt}')
            
            # Text generation using DashScope
            messages = [{'role': 'user', 'content': prompt}]
            
            response = dashscope.Generation.call(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_length,
                result_format='message'
            )
            
            if response.status_code == HTTPStatus.OK:
                generated_text = response.output.choices[0]['message']['content']
                logger.context(logging.INFO, 'Text generation completed')
                
                logger.context(logging.INFO, f'Generated text preview: {generated_text[:200]}...')
                
                # Print AI response content
                logger.context(logging.INFO, 'AI Response Content:')
                logger.context(logging.INFO, '-' * 40)
                logger.context(logging.INFO, generated_text)
                logger.context(logging.INFO, '-' * 40)
                
                logger.context(logging.INFO, '')
                
                return {'response': generated_text}
            else:
                logger.context(logging.ERROR, f'Text generation failed: {response.code}, {response.message}')
                return None
                
        except Exception as e:
            error_msg = f"Text generation API test failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return None
    
    def qwen_create_embeddings(self, model_name: str = None, text: str = None):
        """Test embedding generation API"""
        logger.context(logging.INFO, 'Start testing embedding generation API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test embedding generation API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            # Using text-embedding-v1 model for embeddings
            target_model = "text-embedding-v1"
            
            # Set text
            if not text:
                text = '这是一个测试句子，用于生成嵌入向量。'
            
            logger.context(logging.INFO, f'Using model: {target_model}')
            logger.context(logging.INFO, f'Input text: {text}')
            
            # Call embedding API
            response = dashscope.TextEmbedding.call(
                model=target_model,
                input=text
            )
            
            if response.status_code == HTTPStatus.OK:
                embedding = response.output['embeddings'][0]['embedding']
                vector_length = len(embedding)
                logger.context(logging.INFO, f'Successfully generated embedding, length: {vector_length}')
                
                if vector_length > 0:
                    first_five = embedding[:5]
                    last_five = embedding[-5:] if vector_length > 5 else embedding
                    logger.context(logging.INFO, f'First 5 values: {first_five}')
                    logger.context(logging.INFO, f'Last 5 values: {last_five}')
                
                logger.context(logging.INFO, '')
                return {'embedding': embedding}
            else:
                logger.context(logging.ERROR, f'Embedding generation failed: {response.code}, {response.message}')
                return None
                
        except Exception as e:
            error_msg = f"Embedding generation API test failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return None
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64"""
        logger.context(logging.DEBUG, f'Start encoding image: {image_path}')
        try:
            with open(image_path, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            file_size = Path(image_path).stat().st_size
            logger.context(logging.INFO, f'Image encoding completed: {image_path}, size: {file_size} bytes')
            return encoded_string
        except Exception as e:
            logger.context(logging.ERROR, f'Image encoding failed: {str(e)}')
            raise e
    
    def qwen_extract_image_text(self, image_path: str, model_name: str = None,
                                 temperature: float = 0.1, detail_level: str = 'normal'):
        """Test OCR text extraction from image"""
        logger.context(logging.INFO, f'Start testing OCR text extraction from image, path: {image_path}')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test OCR text extraction from image')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        if not image_path:
            logger.context(logging.WARN, 'No image path provided')
            return None
        
        if not Path(image_path).exists():
            logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            logger.context(logging.INFO, f'Processing image: {image_path}')
            
            # 检查图片格式
            image_suffix = Path(image_path).suffix.lower()
            logger.context(logging.DEBUG, f'Image format: {image_suffix}')
            
            # Encode image to base64
            image_base64 = self.encode_image_to_base64(image_path)
            image_url = f"data:image/{image_suffix[1:]};base64,{image_base64}"
            
            # 获取视觉模型
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                logger.context(logging.WARN, 'No vision model found')
                logger.context(logging.INFO, 'Please make sure you have proper access to Qwen vision models')
                return None
            
            logger.context(logging.INFO, f'Using vision model: {target_model}')
            
            # 根据详细级别设置提示词
            prompt = OCR_DETAIL_LEVELS.get(detail_level, OCR_DETAIL_LEVELS['normal'])
            logger.context(logging.DEBUG, f'Using prompt for detail level "{detail_level}": {prompt[:100]}...')
            
            # Prepare messages for multimodal conversation
            messages = [
                {
                    'role': 'user',
                    'content': [
                        {'text': prompt},
                        {'image': image_url}
                    ]
                }
            ]
            
            logger.context(logging.INFO, f'Starting OCR extraction, detail level: {detail_level}')
            
            # Call multimodal conversation API
            response = MultiModalConversation.call(
                model=target_model,
                messages=messages,
                temperature=temperature
            )
            
            if response.status_code == HTTPStatus.OK:
                ocr_result = response.output.choices[0]['message']['content']
                result_length = len(ocr_result)
                logger.context(logging.INFO, 'OCR extraction completed')
                
                logger.context(logging.INFO, f'OCR result length: {result_length} characters')
                
                if result_length > 0:
                    logger.context(logging.INFO, f'OCR result preview: {ocr_result[:200]}...')
                    
                    # Print AI response content
                    logger.context(logging.INFO, 'AI Response Content:')
                    logger.context(logging.INFO, '-' * 40)
                    logger.context(logging.INFO, ocr_result)
                    logger.context(logging.INFO, '-' * 40)
                else:
                    logger.context(logging.ERROR, 'OCR result is empty')
                    return None
                
                # 保存结果到文件
                output_file = f"qwen_ocr_result_{Path(image_path).stem}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Qwen OCR Extraction Result\n\n")
                    f.write(f"**Source Image**: {image_path}\n")
                    f.write(f"**Model**: {target_model}\n")
                    f.write(f"**Detail Level**: {detail_level}\n")
                    f.write(f"**Result Length**: {result_length} characters\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(ocr_result)
                
                logger.context(logging.INFO, f'OCR result saved to: {output_file}')
                logger.context(logging.INFO, '')
                
                return {
                    'text': ocr_result,
                    'model': target_model,
                    'file': output_file,
                    'length': result_length,
                    'success': result_length > 0
                }
            else:
                logger.context(logging.ERROR, f'OCR extraction failed: {response.code}, {response.message}')
                return None
                
        except Exception as e:
            error_msg = f"OCR test failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return None
    
    def qwen_image_to_markdown(self, image_path: str, model_name: str = None,
                                temperature: float = 0.3, include_metadata: bool = True):
        """Test converting image to Markdown format"""
        logger.context(logging.INFO, f'Start testing image to Markdown conversion, path: {image_path}')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test image to Markdown conversion')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        if not image_path:
            logger.context(logging.WARN, 'No image path provided')
            return None
        
        if not Path(image_path).exists():
            logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            logger.context(logging.INFO, f'Processing image: {image_path}')
            
            # Encode image to base64
            image_base64 = self.encode_image_to_base64(image_path)
            image_suffix = Path(image_path).suffix.lower()
            image_url = f"data:image/{image_suffix[1:]};base64,{image_base64}"
            
            # 获取视觉模型
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                logger.context(logging.WARN, 'No vision model found')
                logger.context(logging.INFO, 'Available vision models:')
                vision_models = [m.name for m in self.available_models 
                                if any(k in m.name.lower() for k in VISION_MODEL_KEYWORDS)]
                for vm in vision_models:
                    logger.context(logging.INFO, f'  - {vm}')
                return None
            
            logger.context(logging.INFO, f'Using vision model: {target_model}')
            
            # 使用宏定义中的提示词
            prompt = MARKDOWN_CONVERSION_PROMPT
            
            # Prepare messages for multimodal conversation
            messages = [
                {
                    'role': 'user',
                    'content': [
                        {'text': prompt},
                        {'image': image_url}
                    ]
                }
            ]
            
            logger.context(logging.INFO, 'Starting Markdown conversion')
            
            # Call multimodal conversation API
            response = MultiModalConversation.call(
                model=target_model,
                messages=messages,
                temperature=temperature
            )
            
            if response.status_code == HTTPStatus.OK:
                markdown_content = response.output.choices[0]['message']['content']
                content_length = len(markdown_content)
                logger.context(logging.INFO, 'Markdown conversion completed')
                
                logger.context(logging.INFO, f'Markdown content length: {content_length} characters')
                
                if content_length > 0:
                    logger.context(logging.INFO, f'Markdown preview: {markdown_content[:200]}...')
                    
                    # Print AI response content
                    logger.context(logging.INFO, 'AI Response Content:')
                    logger.context(logging.INFO, '-' * 40)
                    logger.context(logging.INFO, markdown_content)
                    logger.context(logging.INFO, '-' * 40)
                else:
                    logger.context(logging.WARN, 'Markdown conversion result is empty')
                    
                    # 尝试简单的描述
                    logger.context(logging.INFO, 'Trying simple image description...')
                    simple_prompt = "Describe this image in detail."
                    try:
                        simple_messages = [
                            {
                                'role': 'user',
                                'content': [
                                    {'text': simple_prompt},
                                    {'image': image_url}
                                ]
                            }
                        ]
                        
                        simple_response = MultiModalConversation.call(
                            model=target_model,
                            messages=simple_messages,
                            temperature=temperature
                        )
                        
                        if simple_response.status_code == HTTPStatus.OK:
                            simple_result = simple_response.output.choices[0]['message']['content']
                            if simple_result and len(simple_result) > 0:
                                logger.context(logging.INFO, f'Simple description result: {simple_result[:200]}...')
                                markdown_content = f"# Image Description\n\n{simple_result}"
                                content_length = len(markdown_content)
                        else:
                            logger.context(logging.ERROR, f'Simple description failed: {simple_response.code}, {simple_response.message}')
                            return None
                            
                    except Exception as e:
                        error_msg = f"Simple description failed: {str(e)}"
                        logger.context(logging.ERROR, error_msg)
                        return None
                
                # 保存结果到文件
                output_file = f"qwen_markdown_result_{Path(image_path).stem}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    if include_metadata:
                        f.write(f"# Image to Markdown Result\n\n")
                        f.write(f"**Source Image**: {image_path}\n\n")
                        f.write(f"**Conversion Model**: {target_model}\n\n")
                        f.write(f"**Content Length**: {content_length} characters\n\n")
                        f.write("## Content\n\n")
                    f.write(markdown_content)
                
                logger.context(logging.INFO, f'Markdown result saved to: {output_file}')
                logger.context(logging.INFO, '')
                
                return {
                    'markdown': markdown_content,
                    'model': target_model,
                    'file': output_file,
                    'length': content_length,
                    'success': content_length > 0
                }
            else:
                logger.context(logging.ERROR, f'Markdown conversion failed: {response.code}, {response.message}')
                return None
                
        except Exception as e:
            error_msg = f"Markdown conversion test failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return None
    
    def qwen_describe_image(self, image_path: str, model_name: str = None,
                             detail_level: str = "detailed"):
        """Describe image content"""
        logger.context(logging.INFO, f'Start describing image content: {image_path}')
        
        if not image_path or not Path(image_path).exists():
            logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            # Encode image to base64
            image_base64 = self.encode_image_to_base64(image_path)
            image_suffix = Path(image_path).suffix.lower()
            image_url = f"data:image/{image_suffix[1:]};base64,{image_base64}"
            
            # Get vision model
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                logger.context(logging.WARN, 'No vision model found')
                return None
            
            # Use macro-defined detail level prompts
            prompt = IMAGE_DESCRIPTION_LEVELS.get(detail_level, IMAGE_DESCRIPTION_LEVELS["normal"])
            
            # Prepare messages for multimodal conversation
            messages = [
                {
                    'role': 'user',
                    'content': [
                        {'text': prompt},
                        {'image': image_url}
                    ]
                }
            ]
            
            logger.context(logging.DEBUG, f'Calling multimodal conversation API for image description, detail level: {detail_level}')
            
            # Call multimodal conversation API
            response = MultiModalConversation.call(
                model=target_model,
                messages=messages,
                temperature=0.5
            )
            
            if response.status_code == HTTPStatus.OK:
                description = response.output.choices[0]['message']['content']
                description_length = len(description)
                logger.context(logging.INFO, f'Image description completed, description length: {description_length} characters')
                
                # Print AI response content
                logger.context(logging.INFO, 'AI Response Content:')
                logger.context(logging.INFO, '-' * 40)
                logger.context(logging.INFO, description)
                logger.context(logging.INFO, '-' * 40)
                
                return {
                    'description': description,
                    'model': target_model,
                    'detail_level': detail_level,
                    'length': description_length
                }
            else:
                logger.context(logging.ERROR, f'Image description failed: {response.code}, {response.message}')
                return None
                
        except Exception as e:
            logger.context(logging.ERROR, f'Image description failed: {str(e)}')
            return None
    
    def qwen_analyze_chart(self, image_path: str, model_name: str = None):
        """Analyze chart or diagram"""
        logger.context(logging.INFO, f'Start analyzing chart: {image_path}')
        
        if not image_path or not Path(image_path).exists():
            logger.context(logging.ERROR, f'Image file does not exist: {image_path}')
            return None
            
        try:
            # Encode image to base64
            image_base64 = self.encode_image_to_base64(image_path)
            image_suffix = Path(image_path).suffix.lower()
            image_url = f"data:image/{image_suffix[1:]};base64,{image_base64}"
            
            # Get vision model
            target_model = self._get_model(model_name, 'vision')
            if not target_model:
                logger.context(logging.WARN, 'No vision model found')
                return None
            
            # Use macro-defined chart analysis prompt
            prompt = CHART_ANALYSIS_PROMPT
            
            # Prepare messages for multimodal conversation
            messages = [
                {
                    'role': 'user',
                    'content': [
                        {'text': prompt},
                        {'image': image_url}
                    ]
                }
            ]
            
            logger.context(logging.DEBUG, 'Calling multimodal conversation API for chart analysis')
            
            # Call multimodal conversation API
            response = MultiModalConversation.call(
                model=target_model,
                messages=messages,
                temperature=0.2
            )
            
            if response.status_code == HTTPStatus.OK:
                analysis_result = response.output.choices[0]['message']['content']
                analysis_length = len(analysis_result)
                logger.context(logging.INFO, f'Chart analysis completed, result length: {analysis_length} characters')
                
                # Print AI response content
                logger.context(logging.INFO, 'AI Response Content:')
                logger.context(logging.INFO, '-' * 40)
                logger.context(logging.INFO, analysis_result)
                logger.context(logging.INFO, '-' * 40)
                
                # Save analysis result
                output_file = f"qwen_chart_analysis_{Path(image_path).stem}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Chart Analysis Result\n\n")
                    f.write(f"**Chart File**: {image_path}\n")
                    f.write(f"**Analysis Model**: {target_model}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(analysis_result)
                
                logger.context(logging.INFO, f'Chart analysis result saved to: {output_file}')
                
                return {
                    'analysis': analysis_result,
                    'model': target_model,
                    'file': output_file,
                    'length': analysis_length
                }
            else:
                logger.context(logging.ERROR, f'Chart analysis failed: {response.code}, {response.message}')
                return None
                
        except Exception as e:
            logger.context(logging.ERROR, f'Chart analysis failed: {str(e)}')
            return None
    
    def qwen_check_vision_model(self, model_name: str = None):
        """Check if vision model is available"""
        logger.context(logging.INFO, 'Check if vision model is available')
        try:
            if model_name:
                # Check specific model
                for model in self.available_models:
                    if model.name == model_name:
                        is_vision = any(keyword in model_name.lower() for keyword in VISION_MODEL_KEYWORDS)
                        if is_vision:
                            logger.context(logging.INFO, f'Model {model_name} is a vision model')
                        else:
                            logger.context(logging.WARN, f'Model {model_name} may not be a vision model')
                        return is_vision
                logger.context(logging.WARN, f'Model not found: {model_name}')
                return False
            
            # Check all vision models
            vision_models = []
            for model in self.available_models:
                if any(keyword in model.name.lower() for keyword in VISION_MODEL_KEYWORDS):
                    vision_models.append(model.name)
            
            if vision_models:
                logger.context(logging.INFO, f'Found vision models: {vision_models}')
                return True
            else:
                logger.context(logging.WARN, 'No vision models found')
                return False
                
        except Exception as e:
            logger.context(logging.ERROR, f'Failed to check vision model: {str(e)}')
            return False
    
    def qwen_pull_model(self, model_name: str, verbose: bool = True):
        """Pull model - Not applicable for Qwen API"""
        logger.context(logging.INFO, f'Start testing pull model API, model: {model_name}')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test pull model API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        logger.context(logging.WARN, 'Pull model operation is not supported by Qwen API')
        logger.context(logging.INFO, '')
        return False
    
    def qwen_check_health(self):
        """Test network connectivity"""
        logger.context(logging.INFO, 'Start testing network connectivity')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Test network connectivity')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            # Test network connectivity by making a simple HTTP request
            response = requests.get("https://www.aliyun.com", timeout=10)
            logger.context(logging.INFO, f'Network connectivity check completed, status code: {response.status_code}')
            
            if response.status_code == 200:
                logger.context(logging.INFO, 'Network is accessible')
            else:
                logger.context(logging.WARN, f'Network is accessible but got unexpected status: {response.status_code}')
            
            logger.context(logging.INFO, '')
            return response.status_code == 200
            
        except requests.exceptions.ConnectionError:
            logger.context(logging.ERROR, 'Network is not accessible, please check internet connection')
            return False
        except Exception as e:
            error_msg = f"Network connectivity check failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return False
    
    def qwen_direct_api_test(self):
        """Directly test Qwen API"""
        logger.context(logging.INFO, 'Start directly testing Qwen API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        logger.context(logging.INFO, 'Directly test Qwen API')
        logger.context(logging.INFO, LOG_SEPARATOR)
        
        try:
            # Test if API key is configured properly
            response = dashscope.Generation.call(
                model='qwen-turbo',
                messages=[{'role': 'user', 'content': 'hello'}],
                result_format='message'
            )
            
            if response.status_code == HTTPStatus.OK:
                logger.context(logging.INFO, 'Successfully connected to Qwen API')
                
                # Return mock model list
                parsed_models = [
                    ModelInfo({'name': 'qwen-max', 'model': 'qwen-max'}),
                    ModelInfo({'name': 'qwen-plus', 'model': 'qwen-plus'}),
                    ModelInfo({'name': 'qwen-turbo', 'model': 'qwen-turbo'}),
                    ModelInfo({'name': 'qwen-vl-max', 'model': 'qwen-vl-max'}),
                    ModelInfo({'name': 'qwen-vl-plus', 'model': 'qwen-vl-plus'}),
                ]
                
                self.available_models = parsed_models
                
                # Display model information
                for model in parsed_models:
                    model_info = f"Model: {model.name}"
                    logger.context(logging.INFO, model_info)
                
                logger.context(logging.INFO, '')
                return parsed_models
            else:
                logger.context(logging.ERROR, f'API call failed, status code: {response.status_code}')
                return []
                
        except Exception as e:
            error_msg = f"Direct API test failed: {str(e)}"
            logger.context(logging.ERROR, error_msg)
            return []


# ============ 使用示例 ============

def main():
    """Main function - demonstrate how to use QwenAPITester"""
    
    # Create tester
    # You need to provide your actual API key here
    tester = QwenAPITester(api_key="sk-f220dff5e50b4a46bc1757c04bf5539d")
    
    # Check network connectivity
    if not tester.qwen_check_health():
        logger.context(logging.ERROR, 'Network is not accessible, please check internet connection')
        exit(1)
    
    # List available models
    logger.context(logging.INFO, 'Getting available models...')
    models = tester.qwen_list_models()
    
    if not models:
        logger.context(logging.WARN, 'No available models found')
        exit(1)
    
    # Display model information
    logger.context(logging.INFO, f'Found {len(models)} models:')
    for i, model in enumerate(models, 1):
        model_type = tester._detect_model_type(model.name)
        logger.context(logging.INFO, f'{i}. {model.name} ({model_type})')
    
    # Test chat function
    logger.context(logging.INFO, LOG_SECTION_SEPARATOR)
    logger.context(logging.INFO, f'Test chat function')
    logger.context(logging.INFO, LOG_SECTION_SEPARATOR)
    
    chat_result = tester.qwen_chat_completion(
        model_name='qwen-turbo',
        prompt='请用中文介绍人工智能的发展历程',
        temperature=0.7,
        max_length=300
    )
    
    if chat_result:
        logger.context(logging.INFO, 'Chat test successful')
    else:
        logger.context(logging.ERROR, 'Chat test failed')
    
    # Test embedding function
    logger.context(logging.INFO, LOG_SECTION_SEPARATOR)
    logger.context(logging.INFO, f'Test embedding function')
    logger.context(logging.INFO, LOG_SECTION_SEPARATOR)
    
    embed_result = tester.qwen_create_embeddings(
        text='这是一个测试句子，用于生成嵌入向量。'
    )
    
    if embed_result:
        logger.context(logging.INFO, f'Embedding test successful, vector length: {len(embed_result["embedding"])}')
    else:
        logger.context(logging.ERROR, 'Embedding test failed')
    
    # Test OCR functionality with example image
    test_image_path = "image\\IMG_20260113_215429.jpg"  # Replace with your image path
    if Path(test_image_path).exists():
        logger.context(logging.INFO, LOG_SECTION_SEPARATOR)
        logger.context(logging.INFO, f'Test OCR functionality on image: {test_image_path}')
        logger.context(logging.INFO, LOG_SECTION_SEPARATOR)
        
        ocr_result = tester.qwen_extract_image_text(
            image_path=test_image_path,
            model_name='qwen-vl-max',
            temperature=0.1,
            detail_level='detailed'
        )
        
        if ocr_result:
            logger.context(logging.INFO, f'OCR test successful, recognized text length: {ocr_result["length"]}')
            logger.context(logging.INFO, f'OCR result saved to: {ocr_result["file"]}')
        else:
            logger.context(logging.ERROR, 'OCR test failed')
    else:
        logger.context(logging.WARN, f'Test image does not exist: {test_image_path}')
        logger.context(logging.INFO, 'To test OCR functionality, please provide a valid image file')
    
    logger.context(logging.INFO, 'All tests completed')
    logger.context(logging.INFO, LOG_SECTION_SEPARATOR)


if __name__ == "__main__":
    main()