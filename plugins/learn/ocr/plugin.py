"""
OCR插件 - 基于moduleOcr.py的适配版本
功能：图片选择和文字识别，支持Ollama OCR
"""

import json
import sys
import os
from pathlib import Path

from common.aiFactory.factory import AIProviderFactory, AIProviderType

try:
    # 尝试从QtWidgets导入QAction（某些PyQt6版本）
    from PyQt6.QtWidgets import QAction
except ImportError:
    # 如果失败，尝试从QtGui导入（其他版本）
    from PyQt6.QtGui import QAction

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
    QSizePolicy, QHBoxLayout, QVBoxLayout, QGridLayout, QApplication
)
from PyQt6.QtGui import QPixmap, QClipboard
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# 添加路径以便导入base_plugin
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from plugins.base_plugin import BasePlugin

class OcrPlugin(BasePlugin):
    """OCR图像识别插件 - 支持图片选择和文字识别"""
    
    def __init__(self, plugin_name, ui_file, signal_bus):
        super().__init__(plugin_name, ui_file, signal_bus)
        
        # 初始化变量
        self.current_image_path = None
        self.original_pixmap = None
        self.aiClient = None  # 初始化为None，在initialize中创建
        
        # 配置文件路径
        self.config_file = Path(__file__).parent / "ocr_config.json"
        self.providers_config = {}
        self.logger.context(self.logger.INFO, f"OCR plugin created with UI: {ui_file}")
    
    def load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.providers_config = config.get('providers', {})
                    self.logger.context(self.logger.INFO, f"Loaded config from {self.config_file}")
                    self.logger.context(self.logger.DEBUG, f"Config: {self.providers_config}")
            else:
                # 如果配置文件不存在，创建默认配置
                self.create_default_config()
                self.logger.context(self.logger.INFO, f"Created default config at {self.config_file}")
        except Exception as e:
            error_msg = f"Failed to load config: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            # 创建默认配置作为后备
            self.create_default_config()
    
    def create_default_config(self):
        """创建默认配置文件"""
        try:
            default_config = {
                "providers": {
                    "ollama": {
                        "display_name": "OLLAMA",
                        "params": [
                            {"display": "http://localhost:11434", "value": "http://localhost:11434"},
                            {"display": "http://192.168.1.150:11434", "value": "http://192.168.1.150:11434"}
                        ],
                        "default_param": "http://localhost:11434"
                    },
                    "qwen": {
                        "display_name": "QWEN",
                        "params": [
                            {"display": "sk-f220dff5e50b4a46bc1757c04bf5539d", "value": "sk-f220dff5e50b4a46bc1757c04bf5539d"}
                        ],
                        "default_param": "sk-f220dff5e50b4a46bc1757c04bf5539d"
                    }
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            self.providers_config = default_config.get('providers', {})
            self.logger.context(self.logger.INFO, "Created default configuration")
            
        except Exception as e:
            error_msg = f"Failed to create default config: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            # 使用硬编码的默认配置作为最后的后备
            self.providers_config = {
                "ollama": {
                    "display_name": "OLLAMA",
                    "params": [
                        {"display": "http://localhost:11434", "value": "http://localhost:11434"},
                        {"display": "http://192.168.1.150:11434", "value": "http://192.168.1.150:11434"}
                    ],
                    "default_param": "http://localhost:11434"
                },
                "qwen": {
                    "display_name": "QWEN",
                    "params": [
                        {"display": "sk-f220dff5e50b4a46bc1757c04bf5539d", "value": "sk-f220dff5e50b4a46bc1757c04bf5539d"}
                    ],
                    "default_param": "sk-f220dff5e50b4a46bc1757c04bf5539d"
                }
            }
    
    def initialize(self):
        """初始化插件"""
        try:
            # 加载配置文件
            self.load_config()
            
            # 加载UI文件
            if not self.load_ui():
                self.logger.context(self.logger.ERROR, "Failed to load OCR UI")
                return
            
            # 初始化AI客户端（使用默认配置）
            self.initialize_ai_client()
            
            # 设置provider下拉框
            self.setup_provider_combobox()
            
            # 连接信号槽
            self.connect_signals()
            
            # 设置初始状态
            self.setup_initial_state()
            
            # 发送初始化完成消息
            self.send_message("main_window", {
                'type': 'status',
                'message': f'{self.plugin_name} plugin initialized successfully'
            })
            
            # 发送广播消息
            self.broadcast_message({
                'type': 'plugin_status',
                'plugin': self.plugin_name,
                'status': 'ready',
                'description': 'OCR image text recognition tool'
            })
            
            self.logger.context(self.logger.INFO, "OCR plugin initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize OCR plugin: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message("main_window", {
                'type': 'status',
                'message': f'OCR plugin initialization failed: {str(e)}'
            })
    
    def setup_provider_combobox(self):
        """设置provider下拉框"""
        try:
            if hasattr(self.ui, 'provider'):
                # 清除现有项
                self.ui.provider.clear()
                
                # 从配置文件添加provider选项
                for provider_id, provider_info in self.providers_config.items():
                    display_name = provider_info.get('display_name', provider_id.upper())
                    self.ui.provider.addItem(display_name, provider_id)
                
                # 设置默认选项
                default_index = 0
                if "ollama" in self.providers_config:
                    default_index = self.ui.provider.findData("ollama")
                self.ui.provider.setCurrentIndex(max(default_index, 0))
                
                # 连接provider变化信号
                self.ui.provider.currentIndexChanged.connect(self.on_provider_changed)
                
                # 初始化param下拉框
                self.setup_param_combobox(self.ui.provider.currentData())
                
                self.logger.context(self.logger.DEBUG, "Provider combobox set up")
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to setup provider combobox: {str(e)}")
    
    def setup_param_combobox(self, provider_id):
        """根据provider类型设置param下拉框"""
        try:
            if not hasattr(self.ui, 'param') or provider_id not in self.providers_config:
                return
            
            # 清除现有项
            self.ui.param.clear()
            
            provider_config = self.providers_config[provider_id]
            params = provider_config.get('params', [])
            default_param = provider_config.get('default_param', '')
            
            # 添加参数选项
            for param in params:
                display_text = param.get('display', param.get('value', ''))
                param_value = param.get('value', display_text)
                self.ui.param.addItem(display_text, param_value)
            
            # 设置默认选项
            if default_param and params:
                # 查找默认参数的索引
                default_index = -1
                for i in range(self.ui.param.count()):
                    if self.ui.param.itemData(i) == default_param:
                        default_index = i
                        break
                
                if default_index >= 0:
                    self.ui.param.setCurrentIndex(default_index)
                elif self.ui.param.count() > 0:
                    self.ui.param.setCurrentIndex(0)
            
            self.logger.context(self.logger.DEBUG, f"Param combobox set up for {provider_id}")
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to setup param combobox: {str(e)}")
    
    def initialize_ai_client(self):
        """初始化AI客户端"""
        try:
            if self.aiClient:
                # 清理现有的客户端
                self.aiClient = None
            
            # 获取当前选择的provider类型
            provider_id = None
            if hasattr(self.ui, 'provider'):
                provider_id = self.ui.provider.currentData()
            
            if not provider_id or provider_id not in self.providers_config:
                # 使用默认的ollama作为后备
                provider_id = "ollama"
                self.logger.context(self.logger.WARN, f"Provider {provider_id} not found in config, using ollama as fallback")
            
            # 根据provider类型创建客户端
            if provider_id == "ollama":
                # 获取base_url
                base_url = "http://localhost:11434"  # 默认值
                if hasattr(self.ui, 'param'):
                    selected_param = self.ui.param.currentData()
                    if selected_param:
                        base_url = selected_param
                
                self.aiClient = AIProviderFactory.create_provider(
                    AIProviderType.OLLAMA, 
                    base_url=base_url
                )
                self.logger.context(self.logger.INFO, f"Initialized OLLAMA client with base_url: {base_url}")
                
            elif provider_id == "qwen":
                # 获取api_key
                api_key = None
                if hasattr(self.ui, 'param'):
                    api_key = self.ui.param.currentData()
                
                self.aiClient = AIProviderFactory.create_provider(
                    AIProviderType.QWEN,
                    api_key=api_key
                )
                self.logger.context(self.logger.INFO, "Initialized QWEN client")
                
            else:
                # 默认使用ollama
                self.aiClient = AIProviderFactory.create_provider(
                    AIProviderType.OLLAMA,
                    base_url="http://localhost:11434"
                )
                self.logger.context(self.logger.WARN, f"Unknown provider {provider_id}, using OLLAMA as fallback")
                
        except Exception as e:
            error_msg = f"Failed to initialize AI client: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            # 创建默认客户端作为后备
            self.aiClient = AIProviderFactory.create_provider(
                AIProviderType.OLLAMA,
                base_url="http://localhost:11434"
            )
    
    def connect_signals(self):
        """连接UI控件的信号槽"""
        try:
            # 连接选择图片按钮
            if hasattr(self.ui, 'pushButtonSelectImage'):
                self.ui.pushButtonSelectImage.clicked.connect(self.on_select_image_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Select Image button")
            
            # 连接开始识别按钮
            if hasattr(self.ui, 'pushButtonStartOCR'):
                self.ui.pushButtonStartOCR.clicked.connect(self.on_start_ocr_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Start OCR button")
            
            # 连接复制结果按钮
            if hasattr(self.ui, 'pushButtonCopyResult'):
                self.ui.pushButtonCopyResult.clicked.connect(self.on_copy_result_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Copy Result button")
            
            # 连接清除图片按钮
            if hasattr(self.ui, 'pushButtonClearImage'):
                self.ui.pushButtonClearImage.clicked.connect(self.on_clear_image_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Clear Image button")
            
            # 连接清除文本按钮
            if hasattr(self.ui, 'pushButtonClearText'):
                self.ui.pushButtonClearText.clicked.connect(self.on_clear_text_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Clear Text button")
            
            # 连接发送到编辑器按钮（如果存在）
            if hasattr(self.ui, 'pushButtonSendToEditor'):
                self.ui.pushButtonSendToEditor.clicked.connect(self.on_send_to_editor_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Send to Editor button")
            
            # 连接provider变化信号（如果之前没连接）
            if hasattr(self.ui, 'provider') and not self.ui.provider.receivers(self.ui.provider.currentIndexChanged):
                self.ui.provider.currentIndexChanged.connect(self.on_provider_changed)
            
            # 连接连接测试按钮
            if hasattr(self.ui, 'connectionTest'):
                self.ui.connectionTest.clicked.connect(self.on_connection_test_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Connection Test button")
            
            # 连接param变化信号（如果需要）
            if hasattr(self.ui, 'param'):
                self.ui.param.currentIndexChanged.connect(self.on_param_changed)
                self.logger.context(self.logger.DEBUG, "Connected Param combobox signal")
            
            self.logger.context(self.logger.INFO, "All UI signals connected")
            
        except Exception as e:
            error_msg = f"Failed to connect signals: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def on_provider_changed(self, index):
        """provider下拉框变化事件"""
        try:
            if index < 0:
                return
            
            # 获取选择的provider类型
            provider_type = self.ui.provider.itemData(index)
            self.logger.context(self.logger.INFO, f"Provider changed to: {provider_type}")
            
            # 更新param下拉框
            self.setup_param_combobox(provider_type)
            
            # 更新状态标签（如果存在）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText(f"Provider changed to {provider_type}")
                self.ui.labelStatus.setStyleSheet("color: #FFA500;")
            
            # 重新初始化AI客户端
            self.initialize_ai_client()
            
            # 发送状态消息
            self.send_message("main_window", {
                'type': 'status',
                'message': f'AI provider changed to {provider_type}'
            })
            
        except Exception as e:
            error_msg = f"Failed to handle provider change: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def on_param_changed(self, index):
        """param下拉框变化事件"""
        try:
            if index < 0 or not hasattr(self.ui, 'provider'):
                return
            
            # 获取当前provider类型
            provider_index = self.ui.provider.currentIndex()
            if provider_index < 0:
                return
            
            provider_type = self.ui.provider.itemData(provider_index)
            param_value = self.ui.param.itemData(index)
            
            self.logger.context(self.logger.INFO, f"Param changed for {provider_type}: {param_value}")
            
            # 重新初始化AI客户端
            self.initialize_ai_client()
            
            # 更新状态标签（如果存在）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText(f"Parameter updated for {provider_type}")
                self.ui.labelStatus.setStyleSheet("color: #FFA500;")
            
            # 发送状态消息
            self.send_message("main_window", {
                'type': 'status',
                'message': f'{provider_type} parameter updated'
            })
            
        except Exception as e:
            error_msg = f"Failed to handle param change: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def on_connection_test_clicked(self):
        """连接测试按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Connection Test button clicked")
            
            # 检查是否有AI客户端
            if not self.aiClient:
                error_msg = "AI client not initialized"
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                return
            
            # 更新状态标签（如果存在）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Testing connection...")
                self.ui.labelStatus.setStyleSheet("color: #FFA500;")
            
            # 获取当前provider类型
            provider_type = ""
            if hasattr(self.ui, 'provider'):
                provider_type = self.ui.provider.currentText()
            
            # 调用check_health方法
            self.logger.context(self.logger.INFO, f"Testing connection for {provider_type}")
            is_healthy = self.aiClient.check_health()
            
            # 显示结果
            if is_healthy:
                success_msg = f"{provider_type} connection test successful!"
                self.logger.context(self.logger.INFO, success_msg)
                QMessageBox.information(self.widget, "Success", success_msg)
                
                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText("Connection test successful")
                    self.ui.labelStatus.setStyleSheet("color: #008000;")
            else:
                error_msg = f"{provider_type} connection test failed!"
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                
                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText("Connection test failed")
                    self.ui.labelStatus.setStyleSheet("color: #FF0000;")
            
            # 发送状态消息
            self.send_message("main_window", {
                'type': 'status',
                'message': f'{provider_type} connection test: {"successful" if is_healthy else "failed"}'
            })
            
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)
            
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Connection test error")
                self.ui.labelStatus.setStyleSheet("color: #FF0000;")
    
    def setup_initial_state(self):
        """设置初始状态"""
        try:
            # 设置图片预览标签的初始文本
            if hasattr(self.ui, 'labelImagePreview'):
                self.ui.labelImagePreview.setText("Image Preview Area")
                self.ui.labelImagePreview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.labelImagePreview.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #cccccc;
                        border-radius: 5px;
                        background-color: #f9f9f9;
                        color: #666666;
                        font-size: 14px;
                    }
                """)
            
            # 设置结果文本框的占位符
            if hasattr(self.ui, 'textEditResult'):
                self.ui.textEditResult.setPlaceholderText("OCR results will be displayed here...")
            
            # 设置状态标签（如果存在）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Ready")
                self.ui.labelStatus.setStyleSheet("color: #008000;")
            
            self.logger.context(self.logger.DEBUG, "Initial state set up")
            
        except Exception as e:
            error_msg = f"Failed to set up initial state: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def on_select_image_clicked(self):
        """选择图片按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Select Image button clicked")
            
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self.widget,
                "Select Image",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;All files (*.*)"
            )
            
            if file_path:
                self.current_image_path = file_path
                self.load_image_to_preview(self.current_image_path)
                
                # 发送状态消息
                self.send_message("main_window", {
                    'type': 'status',
                    'message': f'Image selected: {os.path.basename(file_path)}'
                })
                
                self.logger.context(self.logger.INFO, f"Image selected: {file_path}")
            else:
                self.logger.context(self.logger.DEBUG, "Image selection cancelled")
                
        except Exception as e:
            error_msg = f"Failed to select image: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message("main_window", {
                'type': 'status',
                'message': f'Failed to select image: {str(e)}'
            })
    
    def load_image_to_preview(self, image_path):
        """加载图片到预览区域"""
        try:
            if not hasattr(self.ui, 'labelImagePreview'):
                self.logger.context(self.logger.ERROR, "Preview label not found")
                return

            # 加载图片
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                error_msg = f"Invalid image file: {image_path}"
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                return
            
            # 保存原始图片
            self.original_pixmap = pixmap
            
            # 设置label的缩放策略
            self.ui.labelImagePreview.setPixmap(pixmap)
            self.ui.labelImagePreview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.labelImagePreview.setScaledContents(True)  # 允许label缩放图片
            
            # 设置大小策略
            self.ui.labelImagePreview.setSizePolicy(
                QSizePolicy.Policy.Ignored,  # 水平策略
                QSizePolicy.Policy.Ignored   # 垂直策略
            )
            
            # 清除占位文本
            self.ui.labelImagePreview.setText("")
            
            # 更新状态标签（如果存在）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Image loaded")
                self.ui.labelStatus.setStyleSheet("color: #008000;")
            
            self.logger.context(self.logger.INFO, 
                              f"Image loaded to preview: {pixmap.width()}x{pixmap.height()}")
            
        except Exception as e:
            error_msg = f"Failed to load image to preview: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)
    
    def on_start_ocr_clicked(self):
        """开始识别按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Start OCR button clicked")
            
            # 检查是否有图片
            if not self.current_image_path:
                QMessageBox.information(self.widget, "Information", "Please select an image first.")
                self.logger.context(self.logger.WARN, "No image selected for OCR")
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'No image selected for OCR'
                })
                return
            
            # 显示处理状态
            if hasattr(self.ui, 'textEditResult'):
                self.ui.textEditResult.setPlainText("Processing OCR... Please wait.")
            
            # 更新状态标签（如果存在）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Processing OCR...")
                self.ui.labelStatus.setStyleSheet("color: #FFA500;")
            
            # 调用OCR识别函数
            self.logger.context(self.logger.INFO, f"Performing OCR on: {self.current_image_path}")
            ocr_result = self.perform_ocr(self.current_image_path)
            
            if ocr_result is None:
                QMessageBox.warning(self.widget, "Error", "OCR processing failed!")
                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText("OCR failed")
                    self.ui.labelStatus.setStyleSheet("color: #FF0000;")
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'OCR processing failed'
                })
                return
            
            # 显示结果
            if hasattr(self.ui, 'textEditResult'):
                self.ui.textEditResult.setPlainText(ocr_result)
            
            # 更新状态标签（如果存在）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("OCR completed")
                self.ui.labelStatus.setStyleSheet("color: #008000;")
            
            # 发送状态消息
            self.send_message("main_window", {
                'type': 'status',
                'message': f'OCR completed: {len(ocr_result)} characters recognized'
            })
            
            # # 发送消息到编辑器插件
            # self.send_message("editor", {
            #     'type': 'text_data',
            #     'source': 'ocr',
            #     'content': ocr_result,
            #     'timestamp': 'From OCR plugin'
            # })
            
            self.logger.context(self.logger.INFO, 
                              f"OCR completed successfully: {len(ocr_result)} characters")
            
        except Exception as e:
            error_msg = f"Failed to perform OCR: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)
            self.send_message("main_window", {
                'type': 'status',
                'message': f'OCR failed: {str(e)}'
            })
    
    def perform_ocr(self, image_path, model_name=None):
        """
        执行OCR识别
        
        Args:
            image_path: 图片路径
            model_name: 模型名称
            
        Returns:
            OCR识别结果文本或None
        """
        try:
            # 检查服务状态
            if not self.aiClient.check_health():
                error_msg = 'Ollama service not started, please start service first'
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                return None

            # 检查图片是否存在
            if not Path(image_path).exists():
                error_msg = f'Image file does not exist: {image_path}'
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                return None
            
            # 执行OCR
            result = self.aiClient.extract_image_text(
                image_path=image_path,
                model_name="qwen3-vl:235b-cloud",
                temperature=0.01,
                detail_level='simple'
            )
            
            if not result or not result.get('success', False):
                error_msg = 'OCR extraction failed'
                self.logger.context(self.logger.ERROR, error_msg)
                return None
            
            text = result.get('text', '')
            if not text:
                warning_msg = 'OCR returned empty text'
                self.logger.context(self.logger.WARN, warning_msg)
                QMessageBox.information(self.widget, "Information", "No text found in image.")
                return ''
            
            self.logger.context(self.logger.INFO, 
                              f'OCR successful, recognized text length: {len(text)}')
            return text
            
        except Exception as e:
            error_msg = f'OCR process failed: {str(e)}'
            self.logger.context(self.logger.ERROR, error_msg)
            return None
    
    def on_copy_result_clicked(self):
        """复制结果按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Copy Result button clicked")
            
            if not hasattr(self.ui, 'textEditResult'):
                error_msg = "Result text edit not found"
                self.logger.context(self.logger.ERROR, error_msg)
                return
            
            # 获取文本
            text = self.ui.textEditResult.toPlainText()
            if not text.strip():
                QMessageBox.information(self.widget, "Information", "No text to copy.")
                self.logger.context(self.logger.WARN, "No text to copy")
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'No text to copy'
                })
                return
            
            # 修复：直接使用 QApplication.clipboard() 获取剪贴板实例
            clipboard = QApplication.clipboard()
            
            QMessageBox.information(self.widget, "Success", "Text copied to clipboard!")
            
            # 发送状态消息
            self.send_message("main_window", {
                'type': 'status',
                'message': f'Text copied to clipboard ({len(text)} characters)'
            })
            
            self.logger.context(self.logger.INFO, 
                            f"Text copied to clipboard: {len(text)} characters")
            
        except Exception as e:
            error_msg = f"Failed to copy text: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)
    
    def on_send_to_editor_clicked(self):
        """发送到编辑器按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Send to Editor button clicked")
            
            if not hasattr(self.ui, 'textEditResult'):
                error_msg = "Result text edit not found"
                self.logger.context(self.logger.ERROR, error_msg)
                return
            
            text = self.ui.textEditResult.toPlainText()
            
            if text.strip():
                # 发送消息到编辑器插件
                self.send_message("editor", {
                    'type': 'text_data',
                    'source': 'ocr',
                    'content': text,
                    'timestamp': 'From OCR plugin'
                })
                
                # 发送状态消息
                self.send_message("main_window", {
                    'type': 'status',
                    'message': f'Text sent to editor ({len(text)} characters)'
                })
                
                self.logger.context(self.logger.INFO, 
                                  f"Text sent to editor: {len(text)} characters")
            else:
                warning_msg = "No text to send"
                self.logger.context(self.logger.WARN, warning_msg)
                QMessageBox.information(self.widget, "Information", "No text to send.")
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'No text to send to editor'
                })
                
        except Exception as e:
            error_msg = f"Failed to send text to editor: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)
    
    def on_clear_image_clicked(self):
        """清除图片按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Clear Image button clicked")
            
            if hasattr(self.ui, 'labelImagePreview'):
                # 清除图片
                self.ui.labelImagePreview.clear()
                # 显示占位文本
                self.ui.labelImagePreview.setText("Image Preview Area")
                self.ui.labelImagePreview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.labelImagePreview.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #cccccc;
                        border-radius: 5px;
                        background-color: #f9f9f9;
                        color: #666666;
                        font-size: 14px;
                    }
                """)
                
                # 清除原始图片引用
                self.original_pixmap = None
                self.current_image_path = None
                
                # 更新状态标签（如果存在）
                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText("Image cleared")
                    self.ui.labelStatus.setStyleSheet("color: #008000;")
                
                # 发送状态消息
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'Image cleared'
                })
                
                self.logger.context(self.logger.INFO, "Image cleared")
                
        except Exception as e:
            error_msg = f"Failed to clear image: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def on_clear_text_clicked(self):
        """清除文本按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Clear Text button clicked")
            
            if hasattr(self.ui, 'textEditResult'):
                # 清除文本
                self.ui.textEditResult.clear()
                
                # 更新状态标签（如果存在）
                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText("Text cleared")
                    self.ui.labelStatus.setStyleSheet("color: #008000;")
                
                # 发送状态消息
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'Text cleared'
                })
                
                self.logger.context(self.logger.INFO, "Text cleared")
                
        except Exception as e:
            error_msg = f"Failed to clear text: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def on_message(self, sender, data):
        """接收来自其他插件的消息"""
        try:
            message_type = data.get('type', '')
            
            self.logger.context(self.logger.DEBUG, 
                              f"Received message type: {message_type} from {sender}")
            
            if message_type == 'request_ocr':
                # 处理OCR请求
                self.handle_ocr_request(sender, data)
            
            elif message_type == 'status_query':
                # 响应状态查询
                status_info = {
                    'type': 'status_response',
                    'plugin': self.plugin_name,
                    'status': 'running',
                    'initialized': True,
                    'has_image': self.current_image_path is not None
                }
                
                if self.current_image_path:
                    status_info['current_image'] = os.path.basename(self.current_image_path)
                
                self.send_message(sender, status_info)
                self.logger.context(self.logger.DEBUG, "Responded to status query")
            
            elif message_type == 'text_data':
                # 处理文本数据（如果插件需要接收文本）
                self.handle_text_data(sender, data)
            
            elif message_type == 'plugin_command':
                # 处理插件命令
                command = data.get('command', '')
                if command == 'clear_all':
                    self.on_clear_image_clicked()
                    self.on_clear_text_clicked()
                    self.logger.context(self.logger.INFO, "Cleared all via command")
            
            else:
                # 记录未知消息类型
                self.logger.context(self.logger.DEBUG, 
                                  f"Unknown message type: {message_type} from {sender}")
                
        except Exception as e:
            error_msg = f"Error handling message from {sender}: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def handle_ocr_request(self, sender, data):
        """处理OCR请求"""
        try:
            image_path = data.get('image_path', '')
            
            if image_path:
                self.logger.context(self.logger.INFO, f"Processing OCR request from {sender}")
                
                # 设置当前图片路径
                self.current_image_path = image_path
                
                # 加载图片到预览
                self.load_image_to_preview(image_path)
                
                # 执行OCR
                ocr_result = self.perform_ocr(image_path)
                
                if ocr_result:
                    # 显示结果
                    if hasattr(self.ui, 'textEditResult'):
                        self.ui.textEditResult.setPlainText(ocr_result)
                    
                    # 发送结果回请求者
                    self.send_message(sender, {
                        'type': 'ocr_response',
                        'status': 'success',
                        'text': ocr_result,
                        'request_id': data.get('request_id', '')
                    })
                    
                    self.logger.context(self.logger.INFO, 
                                      f"OCR request processed successfully for {sender}")
                else:
                    # 发送失败响应
                    self.send_message(sender, {
                        'type': 'ocr_response',
                        'status': 'failed',
                        'message': 'OCR processing failed',
                        'request_id': data.get('request_id', '')
                    })
                    
                    self.logger.context(self.logger.ERROR, 
                                      f"OCR request failed for {sender}")
            else:
                error_msg = "No image path in OCR request"
                self.logger.context(self.logger.WARN, error_msg)
                self.send_message(sender, {
                    'type': 'ocr_response',
                    'status': 'failed',
                    'message': error_msg,
                    'request_id': data.get('request_id', '')
                })
                
        except Exception as e:
            error_msg = f"Failed to handle OCR request: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'ocr_response',
                'status': 'failed',
                'message': error_msg,
                'request_id': data.get('request_id', '')
            })
    
    def handle_text_data(self, sender, data):
        """处理文本数据（如果需要从其他插件接收文本）"""
        try:
            text = data.get('content', '')
            source = data.get('source', 'unknown')
            
            if text and hasattr(self.ui, 'textEditResult'):
                # 在结果文本框中追加文本
                current_text = self.ui.textEditResult.toPlainText()
                if current_text:
                    self.ui.textEditResult.append(f"\n\n--- From {sender} ({source}) ---\n")
                self.ui.textEditResult.append(text)
                
                self.logger.context(self.logger.INFO, 
                                  f"Text data received from {sender}: {len(text)} characters")
            else:
                self.logger.context(self.logger.WARN, 
                                  f"Received empty text from {sender}")
                
        except Exception as e:
            error_msg = f"Failed to handle text data: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def cleanup(self):
        """清理插件资源"""
        try:
            # 清理资源
            self.original_pixmap = None
            self.current_image_path = None
            
            # 调用父类的清理方法
            super().cleanup()
            
            self.logger.context(self.logger.INFO, "OCR plugin cleanup complete")
            
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Error during cleanup: {str(e)}")