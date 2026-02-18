"""
Quiz Generation Plugin - AI-powered quiz/question generator
功能：基于输入的文本生成测试题（填空、选择、问答题等）
使用PyQt6控件实现交互式测试题界面
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import re

from common.aiFactory.factory import AIProviderFactory, AIProviderType

try:
    from PyQt6.QtWidgets import QAction
except ImportError:
    from PyQt6.QtGui import QAction

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox, QApplication,
    QSizePolicy, QHBoxLayout, QVBoxLayout, QGridLayout, QSpinBox, QCheckBox, QComboBox,
    QScrollArea, QGroupBox, QRadioButton, QLineEdit, QFrame, QSpacerItem,
    QProgressBar, QTabWidget, QSplitter, QListWidget, QListWidgetItem, QStackedWidget
)
from PyQt6.QtGui import QClipboard, QFont, QPalette, QColor, QTextCursor, QTextCharFormat
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.uic import loadUi

# 添加路径以便导入base_plugin
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from plugins.base_plugin import BasePlugin


class QuizQuestionWidget(QFrame):
    """单个测试题控件"""

    def __init__(self, question_data, question_number, parent=None):
        super().__init__(parent)
        self.question_data = question_data
        self.question_number = question_number
        self.user_answer = ""
        self.is_correct = None

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # 题目标题行
        title_layout = QHBoxLayout()

        # 题目编号
        number_label = QLabel(f"Question {self.question_number}")
        number_font = QFont()
        number_font.setBold(True)
        number_font.setPointSize(12)
        number_label.setFont(number_font)
        number_label.setStyleSheet("color: #2c3e50;")

        # 题目类型标签
        q_type = self.question_data.get('Type', 'Unknown')
        type_label = QLabel(q_type)
        type_label.setStyleSheet("""
            QLabel {
                background-color: #3498db;
                color: white;
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
        """)

        title_layout.addWidget(number_label)
        title_layout.addWidget(type_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 问题文本
        question_text = self.question_data.get('Question', 'No question')
        question_label = QLabel(question_text)
        question_label.setWordWrap(True)
        question_label.setStyleSheet("font-size: 14px; margin-top: 10px;")
        layout.addWidget(question_label)

        # 根据题目类型添加输入控件
        self.answer_widget = self.create_answer_widget(q_type)
        if self.answer_widget:
            layout.addWidget(self.answer_widget)

        # 检查按钮和结果显示
        self.result_widget = QWidget()
        result_layout = QHBoxLayout(self.result_widget)
        result_layout.setContentsMargins(0, 10, 0, 0)

        self.check_button = QPushButton("Check Answer")
        self.check_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.check_button.clicked.connect(self.check_answer)

        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font-weight: bold; margin-left: 10px;")

        result_layout.addWidget(self.check_button)
        result_layout.addWidget(self.result_label)
        result_layout.addStretch()

        layout.addWidget(self.result_widget)

        # 分析区域（初始隐藏）
        self.analysis_widget = QWidget()
        self.analysis_widget.setVisible(False)
        analysis_layout = QVBoxLayout(self.analysis_widget)
        analysis_layout.setContentsMargins(10, 10, 10, 10)

        analysis_label = QLabel("Analysis:")
        analysis_label.setStyleSheet("font-weight: bold; color: #2980b9;")
        analysis_layout.addWidget(analysis_label)

        analysis_text = self.question_data.get('Analysis', 'No analysis available')
        self.analysis_text_edit = QTextEdit()
        self.analysis_text_edit.setPlainText(analysis_text)
        self.analysis_text_edit.setReadOnly(True)
        self.analysis_text_edit.setMaximumHeight(100)
        self.analysis_text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                padding: 5px;
                background-color: #f8f9fa;
            }
        """)
        analysis_layout.addWidget(self.analysis_text_edit)

        layout.addWidget(self.analysis_widget)

    def create_answer_widget(self, q_type):
        """根据题目类型创建答案输入控件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        if q_type.lower() == 'choice':
            # 选择题
            options = self.question_data.get('Options', {})
            self.option_buttons = []

            for opt in ['A', 'B', 'C', 'D']:
                if opt in options:
                    radio = QRadioButton(f"{opt}. {options[opt]}")
                    radio.option_value = opt
                    self.option_buttons.append(radio)
                    layout.addWidget(radio)

        elif q_type.lower() == 'fill':
            # 填空题
            label = QLabel("Enter your answer:")
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label)

            self.answer_input = QLineEdit()
            self.answer_input.setPlaceholderText("Type your answer...")
            self.answer_input.setStyleSheet("""
                QLineEdit {
                    padding: 8px;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                }
            """)
            layout.addWidget(self.answer_input)

        elif q_type.lower() == 'q&a':
            # 问答题
            label = QLabel("Enter your answer:")
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label)

            self.answer_input = QTextEdit()
            self.answer_input.setPlaceholderText("Write your answer here...")
            self.answer_input.setMaximumHeight(80)
            self.answer_input.setStyleSheet("""
                QTextEdit {
                    padding: 8px;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                }
            """)
            layout.addWidget(self.answer_input)

        else:
            return None

        return widget

    def get_user_answer(self):
        """获取用户答案"""
        q_type = self.question_data.get('Type', '').lower()

        if q_type == 'choice':
            for radio in self.option_buttons:
                if radio.isChecked():
                    return radio.option_value
            return ""
        elif q_type in ['fill', 'q&a']:
            if hasattr(self, 'answer_input'):
                if isinstance(self.answer_input, QLineEdit):
                    return self.answer_input.text().strip()
                else:  # QTextEdit
                    return self.answer_input.toPlainText().strip()
        return ""

    def check_answer(self):
        """检查答案"""
        user_answer = self.get_user_answer()
        if not user_answer:
            self.result_label.setText("Please enter an answer first")
            self.result_label.setStyleSheet("color: #e74c3c;")
            return

        correct_answer = str(self.question_data.get('Answer', '')).strip()
        q_type = self.question_data.get('Type', '').lower()

        is_correct = False

        if q_type == 'choice':
            is_correct = user_answer.upper() == correct_answer.upper()
        elif q_type == 'fill':
            is_correct = user_answer.lower() == correct_answer.lower()
        elif q_type == 'q&a':
            # 问答题模糊匹配
            is_correct = (user_answer.lower() in correct_answer.lower() or
                         correct_answer.lower() in user_answer.lower())

        self.is_correct = is_correct

        if is_correct:
            self.result_label.setText("✓ Correct!")
            self.result_label.setStyleSheet("color: #27ae60;")
            self.setStyleSheet("""
                QFrame {
                    background-color: #d4edda;
                    border-radius: 5px;
                    border: 2px solid #c3e6cb;
                }
            """)
        else:
            self.result_label.setText(f"✗ Incorrect! Correct answer: {correct_answer}")
            self.result_label.setStyleSheet("color: #e74c3c;")
            self.setStyleSheet("""
                QFrame {
                    background-color: #f8d7da;
                    border-radius: 5px;
                    border: 2px solid #f5c6cb;
                }
            """)

        # 显示分析
        self.analysis_widget.setVisible(True)

        # 发出信号通知父组件更新分数
        if hasattr(self.parent(), 'update_score'):
            self.parent().update_score()

    def reset(self):
        """重置题目状态"""
        q_type = self.question_data.get('Type', '').lower()

        if q_type == 'choice':
            for radio in self.option_buttons:
                radio.setChecked(False)
        elif q_type in ['fill', 'q&a']:
            if hasattr(self, 'answer_input'):
                if isinstance(self.answer_input, QLineEdit):
                    self.answer_input.clear()
                else:
                    self.answer_input.clear()

        self.result_label.setText("")
        self.analysis_widget.setVisible(False)
        self.is_correct = None
        self.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
        """)


class QuizResultWidget(QWidget):
    """测试题结果显示控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.quiz_data = []
        self.question_widgets = []
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 得分面板
        self.score_panel = QFrame()
        self.score_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.score_panel.setStyleSheet("""
            QFrame {
                background-color: #ecf0f1;
                border-radius: 5px;
                padding: 10px;
            }
        """)

        score_layout = QHBoxLayout(self.score_panel)

        self.score_label = QLabel("Score: 0%")
        self.score_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #2c3e50;")

        self.score_detail = QLabel("Correct: 0/0")
        self.score_detail.setStyleSheet("color: #7f8c8d;")

        score_layout.addWidget(self.score_label)
        score_layout.addWidget(self.score_detail)
        score_layout.addStretch()

        # 操作按钮
        button_layout = QHBoxLayout()

        self.check_all_button = QPushButton("Check All")
        self.check_all_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        self.show_all_analysis_button = QPushButton("Show All Analysis")
        self.show_all_analysis_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)

        self.reset_all_button = QPushButton("Reset All")
        self.reset_all_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        button_layout.addWidget(self.check_all_button)
        button_layout.addWidget(self.show_all_analysis_button)
        button_layout.addWidget(self.reset_all_button)

        score_layout.addLayout(button_layout)

        layout.addWidget(self.score_panel)

        # 滚动区域显示所有题目
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                width: 12px;
                background-color: #f5f5f5;
            }
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 6px;
            }
        """)

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)

        # 连接信号
        self.check_all_button.clicked.connect(self.check_all_answers)
        self.show_all_analysis_button.clicked.connect(self.show_all_analysis)
        self.reset_all_button.clicked.connect(self.reset_all_answers)

    def set_quiz_data(self, quiz_data):
        """设置测试题数据"""
        self.quiz_data = quiz_data
        self.question_widgets = []

        # 清除现有题目
        while self.scroll_layout.count() > 1:  # 保留stretch
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新题目
        for i, question in enumerate(quiz_data, 1):
            question_widget = QuizQuestionWidget(question, i)
            self.question_widgets.append(question_widget)
            self.scroll_layout.insertWidget(i-1, question_widget)

        # 更新分数显示
        self.update_score()

    def update_score(self):
        """更新分数显示"""
        if not self.question_widgets:
            return

        correct_count = 0
        total_count = len(self.question_widgets)

        for widget in self.question_widgets:
            if widget.is_correct:
                correct_count += 1

        score = 0
        if total_count > 0:
            score = int((correct_count / total_count) * 100)

        self.score_label.setText(f"Score: {score}%")
        self.score_detail.setText(f"Correct: {correct_count}/{total_count}")

        # 根据分数设置颜色
        if score >= 80:
            self.score_label.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 16px;")
        elif score >= 60:
            self.score_label.setStyleSheet("color: #f39c12; font-weight: bold; font-size: 16px;")
        else:
            self.score_label.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 16px;")

    def check_all_answers(self):
        """检查所有答案"""
        for widget in self.question_widgets:
            widget.check_answer()

    def show_all_analysis(self):
        """显示所有分析"""
        for widget in self.question_widgets:
            widget.analysis_widget.setVisible(True)

    def reset_all_answers(self):
        """重置所有答案"""
        for widget in self.question_widgets:
            widget.reset()
        self.update_score()


class QuizPlugin(BasePlugin):
    """AI Quiz Generation Plugin - 基于文本生成测试题"""

    def __init__(self, plugin_name, ui_file, signal_bus):
        super().__init__(plugin_name, ui_file, signal_bus)

        # 初始化变量
        self.current_source_text = ""
        self.aiClient = None
        self.quiz_data = None
        self.quiz_result_widget = None
        self.fullscreen_mode = False

        # 存储当前加载的文本样式（细粒度格式描述）
        self.current_styles = None

        # 配置文件路径
        self.config_file = Path(__file__).parent / "quiz_config.json"
        self.providers_config = {}
        self.logger.context(self.logger.INFO, f"Quiz plugin created with UI: {ui_file}")

    def _apply_saved_style(self, text_edit: QTextEdit, style_info: dict):
        """将单个样式字典应用到 textEdit 的指定范围"""
        try:
            cursor = QTextCursor(text_edit.document())
            start = style_info.get('start')
            end = style_info.get('end')
            if start is None or end is None or start < 0 or end <= start:
                return

            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

            char_format = QTextCharFormat()

            # 字体样式
            if style_info.get('bold'):
                char_format.setFontWeight(QFont.Weight.Bold)
            if style_info.get('italic'):
                char_format.setFontItalic(True)
            if style_info.get('underline'):
                char_format.setFontUnderline(True)
            if style_info.get('strikethrough'):
                char_format.setFontStrikeOut(True)

            # 前景色
            color_str = style_info.get('color')
            if color_str:
                color = QColor(color_str)
                if color.isValid() and color_str != "#000000":
                    char_format.setForeground(color)

            # 背景色
            bg_str = style_info.get('background')
            if bg_str and bg_str != "#000000":
                bg_color = QColor(bg_str)
                if bg_color.isValid() and bg_color.alpha() > 0:
                    char_format.setBackground(bg_color)

            cursor.mergeCharFormat(char_format)
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to apply style: {e}")

    def _load_styles_for_file(self, text_file_path: str):
        """
        检查是否存在同名的 .txt.json 样式文件，若存在则解析并应用样式到 self.ui.textEditSource
        同时将样式数据保存到 self.current_styles
        """
        self.current_styles = None

        if not hasattr(self.ui, 'textEditSource'):
            return

        style_file = f"{text_file_path}.json"
        if not os.path.exists(style_file):
            self.logger.context(self.logger.DEBUG, f"No style file found: {style_file}")
            return

        try:
            self.logger.context(self.logger.INFO, f"Loading style file: {style_file}")
            with open(style_file, 'r', encoding='utf-8') as f:
                styles_data = json.load(f)

            styles = styles_data.get('styles', [])
            if not isinstance(styles, list):
                self.logger.context(self.logger.WARN, "Invalid styles data: not a list")
                return

            # --- 简化：阻塞信号，防止 textChanged 触发（已移除该信号）---
            self.ui.textEditSource.blockSignals(True)
            # 保存样式列表供后续生成 quiz 使用
            self.current_styles = styles

            self.logger.context(self.logger.DEBUG, f"Applying {len(styles)} style blocks")
            for style_info in styles:
                self._apply_saved_style(self.ui.textEditSource, style_info)

            self.ui.textEditSource.blockSignals(False)

            self.logger.context(self.logger.INFO, f"Styles applied from {style_file}")
        except json.JSONDecodeError as e:
            self.logger.context(self.logger.ERROR, f"Failed to parse style JSON: {e}")
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to load styles: {e}")

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
                self.logger.context(self.logger.ERROR, "Failed to load Quiz UI")
                return

            # 初始化AI客户端（使用默认配置）
            self.initialize_ai_client()

            # 设置provider下拉框
            self.setup_provider_combobox()

            # 设置结果显示区域
            self.setup_result_widget()

            # 连接信号槽
            self.connect_signals()

            # 设置初始状态
            self.setup_initial_state()

            # 动态添加“包含文本样式”复选框（位于题目类型之后）
            self._add_style_checkbox()

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
                'description': 'AI-powered quiz generation tool'
            })

            self.logger.context(self.logger.INFO, "Quiz plugin initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize Quiz plugin: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message("main_window", {
                'type': 'status',
                'message': f'Quiz plugin initialization failed: {str(e)}'
            })

    def _add_style_checkbox(self):
        """在 quizTypeLayout 中添加“包含文本样式”复选框，默认选中，并挂载到 self.ui"""
        try:
            # 避免重复添加
            if hasattr(self.ui, 'checkBoxIncludeStyles'):
                return

            # 创建复选框
            cb = QCheckBox("Include text styles (formatting) in prompt")
            cb.setObjectName("checkBoxIncludeStyles")
            cb.setChecked(True)  # 默认选中
            cb.setToolTip("If checked, the style information (bold, color, etc.) will be sent to AI to help generate quiz")

            # 将控件挂载到 self.ui 上（关键修复！）
            self.ui.checkBoxIncludeStyles = cb

            # 获取布局
            layout = self.ui.quizTypeLayout
            if not layout:
                self.logger.context(self.logger.WARN, "quizTypeLayout not found, cannot add style checkbox")
                return

            # 找到 checkBoxQa 的索引，在其后插入复选框
            index = -1
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and item.widget().objectName() == "checkBoxQa":
                    index = i + 1
                    break

            if index != -1:
                layout.insertWidget(index, cb)
                self.logger.context(self.logger.DEBUG, "Style checkbox added after checkBoxQa")
            else:
                layout.addWidget(cb)
                self.logger.context(self.logger.DEBUG, "Style checkbox appended to layout")

            self.logger.context(self.logger.INFO, "Include styles checkbox is now available in UI")
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to add style checkbox: {e}")

    def setup_result_widget(self):
        """设置结果显示区域"""
        try:
            # 创建交互式结果显示控件
            self.quiz_result_widget = QuizResultWidget()

            # 替换原来的textEditResult
            if hasattr(self.ui, 'textEditResult'):
                text_edit = self.ui.textEditResult

                # 找到textEditResult的父布局
                parent_widget = self.widget
                if hasattr(self.ui, 'gridLayout'):
                    layout = self.ui.gridLayout

                    # 遍历布局项找到textEditResult的位置
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget() == text_edit:
                            # 获取行列信息
                            row, col, rowspan, colspan = layout.getItemPosition(i)

                            # 移除原来的控件
                            layout.removeWidget(text_edit)
                            text_edit.setParent(None)

                            # 添加交互式控件
                            layout.addWidget(self.quiz_result_widget, row, col, rowspan, colspan)

                            self.logger.context(self.logger.INFO, "Result area setup completed")
                            break

        except Exception as e:
            error_msg = f"Failed to setup result widget: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)

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
                self.aiClient = None

            # 获取当前选择的provider类型
            provider_id = None
            if hasattr(self.ui, 'provider'):
                provider_id = self.ui.provider.currentData()

            if not provider_id or provider_id not in self.providers_config:
                provider_id = "ollama"
                self.logger.context(self.logger.WARN, f"Provider {provider_id} not found in config, using ollama as fallback")

            if provider_id == "ollama":
                base_url = "http://localhost:11434"
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
                api_key = None
                if hasattr(self.ui, 'param'):
                    api_key = self.ui.param.currentData()

                self.aiClient = AIProviderFactory.create_provider(
                    AIProviderType.QWEN,
                    api_key=api_key
                )
                self.logger.context(self.logger.INFO, "Initialized QWEN client")

            else:
                self.aiClient = AIProviderFactory.create_provider(
                    AIProviderType.OLLAMA,
                    base_url="http://localhost:11434"
                )
                self.logger.context(self.logger.WARN, f"Unknown provider {provider_id}, using OLLAMA as fallback")

        except Exception as e:
            error_msg = f"Failed to initialize AI client: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.aiClient = AIProviderFactory.create_provider(
                AIProviderType.OLLAMA,
                base_url="http://localhost:11434"
            )

    def connect_signals(self):
        """连接UI控件的信号槽"""
        try:
            # 连接加载文本按钮
            if hasattr(self.ui, 'pushButtonLoadText'):
                self.ui.pushButtonLoadText.clicked.connect(self.on_load_text_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Load Text button")

            # 连接生成测试题按钮
            if hasattr(self.ui, 'pushButtonGenerateQuiz'):
                self.ui.pushButtonGenerateQuiz.clicked.connect(self.on_generate_quiz_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Generate Quiz button")

            # 连接复制结果按钮
            if hasattr(self.ui, 'pushButtonCopyResult'):
                self.ui.pushButtonCopyResult.clicked.connect(self.on_copy_result_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Copy Result button")

            # 连接清除源文本按钮
            if hasattr(self.ui, 'pushButtonClearSource'):
                self.ui.pushButtonClearSource.clicked.connect(self.on_clear_source_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Clear Source button")

            # 连接清除结果按钮
            if hasattr(self.ui, 'pushButtonClearResult'):
                self.ui.pushButtonClearResult.clicked.connect(self.on_clear_result_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Clear Result button")

            # 连接导出测试题按钮
            if hasattr(self.ui, 'pushButtonExportQuiz'):
                self.ui.pushButtonExportQuiz.clicked.connect(self.on_export_quiz_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Export Quiz button")

            # 连接导入测试题按钮
            if hasattr(self.ui, 'pushButtonImportQuiz'):
                self.ui.pushButtonImportQuiz.clicked.connect(self.on_import_quiz_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Import Quiz button")

            # 连接全屏模式按钮
            if hasattr(self.ui, 'pushButtonFullscreen'):
                self.ui.pushButtonFullscreen.clicked.connect(self.toggle_fullscreen_mode)
                self.logger.context(self.logger.DEBUG, "Connected Fullscreen button")

            # 连接provider变化信号
            if hasattr(self.ui, 'provider') and not self.ui.provider.receivers(self.ui.provider.currentIndexChanged):
                self.ui.provider.currentIndexChanged.connect(self.on_provider_changed)

            # 连接连接测试按钮
            if hasattr(self.ui, 'connectionTest'):
                self.ui.connectionTest.clicked.connect(self.on_connection_test_clicked)
                self.logger.context(self.logger.DEBUG, "Connected Connection Test button")

            # 连接param变化信号
            if hasattr(self.ui, 'param'):
                self.ui.param.currentIndexChanged.connect(self.on_param_changed)
                self.logger.context(self.logger.DEBUG, "Connected Param combobox signal")

            # --- 移除 textChanged 信号连接 ---

            self.logger.context(self.logger.INFO, "All UI signals connected")

        except Exception as e:
            error_msg = f"Failed to connect signals: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)

    def toggle_fullscreen_mode(self):
        """切换全屏模式"""
        try:
            if not hasattr(self.ui, 'textEditSource') or not hasattr(self.ui, 'gridLayout'):
                return

            self.fullscreen_mode = not self.fullscreen_mode

            if self.fullscreen_mode:
                # 切换到全屏模式：隐藏原文预览，问答区域占满
                self.ui.textEditSource.setVisible(False)
                self.ui.pushButtonFullscreen.setText("Show Source")
                self.ui.pushButtonFullscreen.setToolTip("Switch to normal mode, show source and quiz")

                # 调整布局
                layout = self.ui.gridLayout

                # 找到问答区域的位置
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == self.quiz_result_widget:
                        row, col, rowspan, colspan = layout.getItemPosition(i)
                        # 让问答区域占据整个第2行
                        layout.addWidget(self.quiz_result_widget, row, 0, rowspan, 2)
                        break

                self.logger.context(self.logger.INFO, "Switched to fullscreen mode")
            else:
                # 切换到正常模式：显示原文预览，恢复布局
                self.ui.textEditSource.setVisible(True)
                self.ui.pushButtonFullscreen.setText("Full Screen")
                self.ui.pushButtonFullscreen.setToolTip("Switch to fullscreen mode, hide source text")

                # 恢复布局
                layout = self.ui.gridLayout

                # 找到问答区域的位置
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == self.quiz_result_widget:
                        row, col, rowspan, colspan = layout.getItemPosition(i)
                        # 让问答区域恢复到第2行第1列
                        layout.addWidget(self.quiz_result_widget, row, 1, rowspan, 1)
                        break

                self.logger.context(self.logger.INFO, "Switched to normal mode")

        except Exception as e:
            error_msg = f"Failed to toggle fullscreen mode: {str(e)}"
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

            provider_index = self.ui.provider.currentIndex()
            if provider_index < 0:
                return

            provider_type = self.ui.provider.itemData(provider_index)
            param_value = self.ui.param.itemData(index)

            self.logger.context(self.logger.INFO, f"Param changed for {provider_type}: {param_value}")

            # 重新初始化AI客户端
            self.initialize_ai_client()

            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText(f"Parameter updated for {provider_type}")
                self.ui.labelStatus.setStyleSheet("color: #FFA500;")

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

            if not self.aiClient:
                error_msg = "AI client not initialized"
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                return

            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Testing connection...")
                self.ui.labelStatus.setStyleSheet("color: #FFA500;")

            provider_type = ""
            if hasattr(self.ui, 'provider'):
                provider_type = self.ui.provider.currentText()

            self.logger.context(self.logger.INFO, f"Testing connection for {provider_type}")
            is_healthy = self.aiClient.check_health()

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
            if hasattr(self.ui, 'comboBoxDifficulty'):
                self.ui.comboBoxDifficulty.setCurrentIndex(1)

            if hasattr(self.ui, 'spinBoxQuestionCount'):
                self.ui.spinBoxQuestionCount.setValue(5)

            if hasattr(self.ui, 'checkBoxMultipleChoice'):
                self.ui.checkBoxMultipleChoice.setChecked(True)
            if hasattr(self.ui, 'checkBoxFillBlank'):
                self.ui.checkBoxFillBlank.setChecked(True)
            if hasattr(self.ui, 'checkBoxQa'):
                self.ui.checkBoxQa.setChecked(True)

            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Ready")
                self.ui.labelStatus.setStyleSheet("color: #008000;")

            if hasattr(self.ui, 'pushButtonFullscreen'):
                self.ui.pushButtonFullscreen.setText("Full Screen")
                self.ui.pushButtonFullscreen.setToolTip("Switch to fullscreen mode, hide source text")

            self.logger.context(self.logger.DEBUG, "Initial state set up")

        except Exception as e:
            error_msg = f"Failed to set up initial state: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)

    def on_load_text_clicked(self):
        """加载文本按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Load Text button clicked")

            file_path, _ = QFileDialog.getOpenFileName(
                self.widget,
                "Load Text File",
                "",
                "Text files (*.txt *.md *.json *.csv *.xml);;All files (*.*)"
            )

            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if hasattr(self.ui, 'textEditSource'):
                    # 加载新文本前解除只读，以便设置文本
                    self.ui.textEditSource.setReadOnly(False)
                    self.ui.textEditSource.setPlainText(content)
                    self.current_source_text = content

                    # 加载并应用同名的样式文件
                    self._load_styles_for_file(file_path)

                    # 锁定编辑，防止样式索引错乱
                    self.ui.textEditSource.setReadOnly(True)

                self.send_message("main_window", {
                    'type': 'status',
                    'message': f'Text loaded from: {os.path.basename(file_path)}'
                })

                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText(f"Text loaded: {os.path.basename(file_path)}")
                    self.ui.labelStatus.setStyleSheet("color: #008000;")

                self.logger.context(self.logger.INFO, f"Text loaded from: {file_path}")
            else:
                self.logger.context(self.logger.DEBUG, "Text file selection cancelled")

        except Exception as e:
            error_msg = f"Failed to load text file: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)

    def on_generate_quiz_clicked(self):
        """生成测试题按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Generate Quiz button clicked")

            if hasattr(self.ui, 'textEditSource'):
                source_text = self.ui.textEditSource.toPlainText().strip()
                self.current_source_text = source_text

            if not self.current_source_text:
                QMessageBox.information(self.widget, "Information", "Please enter or load source text first.")
                self.logger.context(self.logger.WARN, "No source text for quiz generation")
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'No source text for quiz generation'
                })
                return

            has_question_type = False
            if hasattr(self.ui, 'checkBoxMultipleChoice') and self.ui.checkBoxMultipleChoice.isChecked():
                has_question_type = True
            if hasattr(self.ui, 'checkBoxFillBlank') and self.ui.checkBoxFillBlank.isChecked():
                has_question_type = True
            if hasattr(self.ui, 'checkBoxQa') and self.ui.checkBoxQa.isChecked():
                has_question_type = True

            if not has_question_type:
                QMessageBox.information(self.widget, "Information", "Please select at least one question type.")
                self.logger.context(self.logger.WARN, "No question type selected")
                return

            question_count = 5
            if hasattr(self.ui, 'spinBoxQuestionCount'):
                question_count = self.ui.spinBoxQuestionCount.value()

            difficulty = "Medium"
            if hasattr(self.ui, 'comboBoxDifficulty'):
                difficulty = self.ui.comboBoxDifficulty.currentText()

            question_types = []
            if hasattr(self.ui, 'checkBoxMultipleChoice') and self.ui.checkBoxMultipleChoice.isChecked():
                question_types.append("multiple choice")
            if hasattr(self.ui, 'checkBoxFillBlank') and self.ui.checkBoxFillBlank.isChecked():
                question_types.append("fill in the blank")
            if hasattr(self.ui, 'checkBoxQa') and self.ui.checkBoxQa.isChecked():
                question_types.append("short answer")

            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Generating quiz... Please wait.")
                self.ui.labelStatus.setStyleSheet("color: #FFA500;")

            QApplication.processEvents()

            self.logger.context(self.logger.INFO, f"Generating quiz with {question_count} questions")
            quiz_data = self.generate_quiz(
                source_text=self.current_source_text,
                question_types=question_types,
                question_count=question_count,
                difficulty=difficulty
            )

            if quiz_data is None:
                QMessageBox.warning(self.widget, "Error", "Quiz generation failed!")
                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText("Quiz generation failed")
                    self.ui.labelStatus.setStyleSheet("color: #FF0000;")
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'Quiz generation failed'
                })
                return

            self.quiz_data = quiz_data

            if self.quiz_result_widget:
                self.quiz_result_widget.set_quiz_data(quiz_data)

            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText(f"Quiz generated: {len(quiz_data)} questions")
                self.ui.labelStatus.setStyleSheet("color: #008000;")

            self.send_message("main_window", {
                'type': 'status',
                'message': f'Quiz generated: {len(quiz_data)} questions created'
            })

            self.logger.context(self.logger.INFO,
                            f"Quiz generation completed successfully: {len(quiz_data)} questions")

        except Exception as e:
            error_msg = f"Failed to generate quiz: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)
            self.send_message("main_window", {
                'type': 'status',
                'message': f'Quiz generation failed: {str(e)}'
            })

    def _build_style_description(self, styles, text):
        """
        将样式数据（self.current_styles）转换为易读的文本描述，
        仅提取具有显著样式（加粗、颜色、背景等）的片段，并限制数量和长度。
        """
        if not styles or not text:
            return "No style information available."

        descriptions = []
        MAX_STYLES = 20
        MAX_FRAGMENT_LEN = 30

        processed = 0
        for style in styles:
            if processed >= MAX_STYLES:
                descriptions.append(f"... and {len(styles)-MAX_STYLES} more style blocks.")
                break

            start = style.get('start')
            end = style.get('end')
            if start is None or end is None or start < 0 or end <= start:
                continue
            if start >= len(text) or end > len(text):
                continue

            fragment = text[start:end]
            if len(fragment) > MAX_FRAGMENT_LEN:
                fragment = fragment[:MAX_FRAGMENT_LEN-3] + "..."
            fragment = fragment.replace('\n', ' ').replace('\r', ' ').strip()
            if not fragment:
                continue

            attrs = []
            if style.get('bold'):
                attrs.append("bold")
            if style.get('italic'):
                attrs.append("italic")
            if style.get('underline'):
                attrs.append("underline")
            if style.get('strikethrough'):
                attrs.append("strikethrough")

            color = style.get('color')
            if color and color.lower() != "#000000":
                attrs.append(f"color {color}")
            background = style.get('background')
            if background and background.lower() != "#000000":
                attrs.append(f"background {background}")

            if not attrs:
                continue

            attrs_str = ", ".join(attrs)
            desc = f"'{fragment}' (positions {start}-{end}) is {attrs_str}."
            descriptions.append(desc)
            processed += 1

        if not descriptions:
            return "No significant style differences detected."

        return "\n".join(descriptions)

    def generate_quiz(self, source_text, question_types, question_count=5, difficulty="Medium"):
        """
        生成测试题（自动匹配源文本语言）
        如果用户勾选了“包含文本样式”且当前有样式数据，则附加样式描述（非完整JSON）
        """
        try:
            # 检测语言
            def detect_language(text):
                if re.search(r'[\u4e00-\u9fff]', text):
                    return "Chinese"
                else:
                    return "English"

            target_lang = detect_language(source_text)
            self.logger.context(self.logger.INFO, f"Detected source text language: {target_lang}")

            if not self.aiClient.check_health():
                error_msg = 'AI service not available, please check connection'
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                return None

            type_mapping = {
                "multiple choice": "choice",
                "fill in the blank": "fill",
                "short answer": "Q&A"
            }
            question_types_short = [type_mapping.get(qt, qt) for qt in question_types]
            question_types_str = ", ".join(question_types)
            question_types_short_str = ", ".join(question_types_short)

            prompt = f"""Based on the following text, generate a quiz with exactly {question_count} questions in JSON format.

Text to analyze:
{source_text[:16384]}...\n\n"""

            # 包含样式描述（如果启用）
            include_styles = (hasattr(self.ui, 'checkBoxIncludeStyles') and
                              self.ui.checkBoxIncludeStyles.isChecked())
            if include_styles and self.current_styles:
                self.logger.context(self.logger.INFO, "Including text style description in prompt")
                style_description = self._build_style_description(self.current_styles, source_text)
                style_prompt = f"""
Additionally, the following text style information (character indices and formatting) is available for the source text.
These styles (bold, color, background, etc.) indicate important or emphasized parts. Use this information to identify key points for generating quiz questions.
Style descriptions:
{style_description}

"""
                prompt += style_prompt

            prompt += f"""
Requirements:
0. **IMPORTANT**: Generate all questions (including Question text, Options, Answer, and Analysis) in **{target_lang}**.
   If the source text is Chinese, all output must be in Chinese; if the source text is English, output must be in English.
1. Create exactly {question_count} questions
2. ONLY generate the following question types: {question_types_str}
3. DO NOT generate any other question types
4. Difficulty level: {difficulty}
5. Return the result as a valid JSON array of objects
6. Each question object must follow these formats:

"""

            if "multiple choice" in question_types:
                prompt += """For multiple choice questions (type: "choice"):
    {{
        "Type": "choice",
        "Number": 1,
        "Question": "Question text here",
        "Options": {{
            "A": "Option A text",
            "B": "Option B text",
            "C": "Option C text",
            "D": "Option D text"
        }},
        "Answer": "Correct answer letter (A, B, C, or D)",
        "Analysis": "Analyze the answer to the question and provide the source from the text"
    }}

"""

            if "fill in the blank" in question_types:
                prompt += """For fill-in-the-blank questions (type: "fill"):
    {{
        "Type": "fill",
        "Number": 2,
        "Question": "Sentence with blank indicated by ___, e.g., The capital of France is ___.",
        "Answer": "Correct answer to fill the blank",
        "Analysis": "Analyze the answer to the question and provide the source from the text"
    }}

"""

            if "short answer" in question_types:
                prompt += """For Q&A questions (type: "Q&A"):
    {{
        "Type": "Q&A",
        "Number": 3,
        "Question": "Question text here",
        "Answer": "Detailed answer to the question",
        "Analysis": "Analyze the answer to the question and provide the source from the text"
    }}

"""

            prompt += f"""
    Important instructions:
    1. The response must be ONLY a valid JSON array, no additional text
    2. ONLY generate questions of the specified types: {question_types_str}
    3. For multiple choice questions, always provide exactly 4 options (A, B, C, D)
    4. For fill-in-the-blank questions, use "___" to indicate blanks in the question
    5. For Analysis field, explain why the answer is correct and cite the specific part of the source text
    6. Number questions sequentially from 1 to {question_count}
    7. Distribute the {question_count} questions evenly among the selected question types
    8. If only one question type is selected, generate all {question_count} questions of that type
    9. **ALL text content (Question, Options, Answer, Analysis) must be in {target_lang}.**

    Generate the quiz now and return ONLY the JSON array:"""

            self.logger.context(self.logger.INFO, f"Calling AI to generate quiz in {target_lang}, types: {question_types_str}")
            result = self.aiClient.chat_completion(
                prompt=prompt,
                temperature=0.3,
                max_length=3000
            )

            if not result:
                error_msg = 'Quiz generation failed - no response from AI'
                self.logger.context(self.logger.ERROR, error_msg)
                return None

            if isinstance(result, dict) and 'message' in result:
                response_text = result['message'].get('content', '')
            elif isinstance(result, dict) and 'response' in result:
                response_text = result['response']
            else:
                response_text = str(result)

            if not response_text:
                warning_msg = 'AI returned empty response'
                self.logger.context(self.logger.WARN, warning_msg)
                QMessageBox.information(self.widget, "Information", "No quiz generated.")
                return []

            try:
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text

                print(f"json_str: \n{json_str}")
                quiz_data = json.loads(json_str)

                if not isinstance(quiz_data, list):
                    raise ValueError("Response is not a JSON array")

                generated_types = set([q.get('Type', '').lower() for q in quiz_data])
                expected_types = set(question_types_short)
                unexpected_types = generated_types - expected_types

                if unexpected_types:
                    self.logger.context(self.logger.WARN,
                                      f"AI generated unexpected question types: {unexpected_types}")

                self.logger.context(self.logger.INFO,
                                  f'Quiz generation successful, {len(quiz_data)} questions generated')
                return quiz_data

            except (json.JSONDecodeError, ValueError) as e:
                error_msg = f'Failed to parse JSON response: {str(e)}'
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", f"Quiz generation failed: {error_msg}")
                return None

        except Exception as e:
            error_msg = f'Quiz generation failed: {str(e)}'
            self.logger.context(self.logger.ERROR, error_msg)
            return None

    def generate_plain_text(self, quiz_data):
        """生成纯文本格式（用于导出）"""
        if not quiz_data:
            return ""

        formatted_output = []

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        provider_name = self.ui.provider.currentText() if hasattr(self.ui, 'provider') and self.ui.provider.count() > 0 else 'Unknown'
        header = f"""QUIZ GENERATED
Source: {len(self.current_source_text)} characters
Questions: {len(quiz_data)}
Generated: {timestamp}
Provider: {provider_name}

{'='*60}

"""
        formatted_output.append(header)

        type_counts = {}
        for question in quiz_data:
            q_type = question.get('Type', 'Unknown')
            type_counts[q_type] = type_counts.get(q_type, 0) + 1

        if type_counts:
            formatted_output.append("Question Type Distribution:")
            for q_type, count in type_counts.items():
                formatted_output.append(f"  {q_type}: {count} question(s)")
            formatted_output.append("")

        for i, question in enumerate(quiz_data, 1):
            formatted_output.append(f"QUESTION {i}")
            formatted_output.append(f"Type: {question.get('Type', 'Unknown')}")
            formatted_output.append(f"Question: {question.get('Question', 'No question')}")

            if question.get('Type', '').lower() == 'choice':
                options = question.get('Options', {})
                if options:
                    formatted_output.append("Options:")
                    for opt in ['A', 'B', 'C', 'D']:
                        if opt in options:
                            formatted_output.append(f"  {opt}. {options[opt]}")
                else:
                    formatted_output.append("Options: Not provided")

            formatted_output.append(f"Answer: {question.get('Answer', 'No answer')}")
            formatted_output.append(f"Analysis: {question.get('Analysis', 'No analysis')}")
            formatted_output.append("-" * 40)
            formatted_output.append("")

        formatted_output.append("\n" + "="*60)
        formatted_output.append("RAW JSON DATA:")
        formatted_output.append("="*60 + "\n")
        formatted_output.append(json.dumps(quiz_data, indent=2, ensure_ascii=False))

        return "\n".join(formatted_output)

    def on_copy_result_clicked(self):
        """复制结果按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Copy Result button clicked")

            if not self.quiz_data:
                QMessageBox.information(self.widget, "Information", "No quiz to copy.")
                self.logger.context(self.logger.WARN, "No quiz to copy")
                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'No quiz to copy'
                })
                return

            text = self.generate_plain_text(self.quiz_data)

            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                error_msg = "No QApplication instance found"
                self.logger.context(self.logger.ERROR, error_msg)
                QMessageBox.warning(self.widget, "Error", error_msg)
                return

            clipboard = app.clipboard()
            clipboard.setText(text)

            QMessageBox.information(self.widget, "Success", "Quiz copied to clipboard!")

            self.send_message("main_window", {
                'type': 'status',
                'message': f'Quiz copied to clipboard ({len(text)} characters)'
            })

            self.logger.context(self.logger.INFO,
                            f"Quiz copied to clipboard: {len(text)} characters")

        except Exception as e:
            error_msg = f"Failed to copy quiz: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)

    def on_export_quiz_clicked(self):
        """导出测试题按钮点击事件（仅JSON格式）"""
        try:
            self.logger.context(self.logger.INFO, "Export Quiz button clicked")

            if not self.quiz_data:
                QMessageBox.information(self.widget, "Information", "No quiz to export.")
                self.logger.context(self.logger.WARN, "No quiz to export")
                return

            default_name = f"quiz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self.widget,
                "Export Quiz as JSON",
                default_name,
                "JSON files (*.json)"
            )

            if file_path:
                if not file_path.lower().endswith('.json'):
                    file_path += '.json'

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.quiz_data, f, indent=2, ensure_ascii=False)

                QMessageBox.information(self.widget, "Success", f"Quiz exported to:\n{file_path}")

                self.send_message("main_window", {
                    'type': 'status',
                    'message': f'Quiz exported to {os.path.basename(file_path)}'
                })

                self.logger.context(self.logger.INFO, f"Quiz exported to: {file_path}")
            else:
                self.logger.context(self.logger.DEBUG, "Quiz export cancelled")

        except Exception as e:
            error_msg = f"Failed to export quiz: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)

    def on_import_quiz_clicked(self):
        """导入测试题按钮点击事件（JSON文件）"""
        try:
            self.logger.context(self.logger.INFO, "Import Quiz button clicked")

            file_path, _ = QFileDialog.getOpenFileName(
                self.widget,
                "Import Quiz from JSON",
                "",
                "JSON files (*.json)"
            )

            if not file_path:
                self.logger.context(self.logger.DEBUG, "Import cancelled")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                quiz_data = json.load(f)

            if not isinstance(quiz_data, list) or len(quiz_data) == 0:
                raise ValueError("Invalid quiz data format: expected a non-empty array")

            self.quiz_data = quiz_data
            if self.quiz_result_widget:
                self.quiz_result_widget.set_quiz_data(quiz_data)

            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText(f"Quiz imported: {len(quiz_data)} questions")
                self.ui.labelStatus.setStyleSheet("color: #008000;")

            self.send_message("main_window", {
                'type': 'status',
                'message': f'Quiz imported from {os.path.basename(file_path)} ({len(quiz_data)} questions)'
            })

            self.logger.context(self.logger.INFO, f"Quiz imported from: {file_path}")

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON file: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)
        except Exception as e:
            error_msg = f"Failed to import quiz: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.warning(self.widget, "Error", error_msg)

    def on_clear_source_clicked(self):
        """清除源文本按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Clear Source button clicked")

            if hasattr(self.ui, 'textEditSource'):
                # 清除前先解除只读，以便清空文本
                self.ui.textEditSource.setReadOnly(False)
                self.ui.textEditSource.clear()
                self.current_source_text = ""
                self.current_styles = None

                if hasattr(self.ui, 'labelStatus'):
                    self.ui.labelStatus.setText("Source text cleared")
                    self.ui.labelStatus.setStyleSheet("color: #008000;")

                self.send_message("main_window", {
                    'type': 'status',
                    'message': 'Source text cleared'
                })

                self.logger.context(self.logger.INFO, "Source text cleared")

        except Exception as e:
            error_msg = f"Failed to clear source text: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)

    def on_clear_result_clicked(self):
        """清除结果按钮点击事件"""
        try:
            self.logger.context(self.logger.INFO, "Clear Result button clicked")

            self.quiz_data = None

            if self.quiz_result_widget:
                self.quiz_result_widget.set_quiz_data([])

            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Quiz cleared")
                self.ui.labelStatus.setStyleSheet("color: #008000;")

            self.send_message("main_window", {
                'type': 'status',
                'message': 'Quiz cleared'
            })

            self.logger.context(self.logger.INFO, "Quiz cleared")

        except Exception as e:
            error_msg = f"Failed to clear quiz: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)

    def on_message(self, sender, data):
        """接收来自其他插件的消息"""
        try:
            message_type = data.get('type', '')

            self.logger.context(self.logger.DEBUG,
                              f"Received message type: {message_type} from {sender}")

            if message_type == 'request_quiz':
                self.handle_quiz_request(sender, data)

            elif message_type == 'status_query':
                status_info = {
                    'type': 'status_response',
                    'plugin': self.plugin_name,
                    'status': 'running',
                    'initialized': True,
                    'has_source': bool(self.current_source_text.strip())
                }

                self.send_message(sender, status_info)
                self.logger.context(self.logger.DEBUG, "Responded to status query")

            elif message_type == 'text_data':
                self.handle_text_data(sender, data)

            elif message_type == 'plugin_command':
                command = data.get('command', '')
                if command == 'clear_all':
                    self.on_clear_source_clicked()
                    self.on_clear_result_clicked()
                    self.logger.context(self.logger.INFO, "Cleared all via command")

            else:
                self.logger.context(self.logger.DEBUG,
                                  f"Unknown message type: {message_type} from {sender}")

        except Exception as e:
            error_msg = f"Error handling message from {sender}: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)

    def handle_quiz_request(self, sender, data):
        """处理测试题生成请求"""
        try:
            source_text = data.get('text', '')
            question_count = data.get('question_count', 5)
            question_types = data.get('question_types', ['multiple choice', 'fill in the blank', 'short answer'])
            difficulty = data.get('difficulty', 'Medium')

            if source_text:
                self.logger.context(self.logger.INFO, f"Processing quiz request from {sender}")

                self.current_source_text = source_text

                if hasattr(self.ui, 'textEditSource'):
                    # 接收外部文本时也设为只读
                    self.ui.textEditSource.setReadOnly(False)
                    self.ui.textEditSource.setPlainText(source_text)
                    self.ui.textEditSource.setReadOnly(True)

                quiz_data = self.generate_quiz(
                    source_text=source_text,
                    question_types=question_types,
                    question_count=question_count,
                    difficulty=difficulty
                )

                if quiz_data:
                    if self.quiz_result_widget:
                        self.quiz_result_widget.set_quiz_data(quiz_data)

                    self.send_message(sender, {
                        'type': 'quiz_response',
                        'status': 'success',
                        'quiz_data': quiz_data,
                        'request_id': data.get('request_id', '')
                    })

                    self.logger.context(self.logger.INFO,
                                      f"Quiz request processed successfully for {sender}")
                else:
                    self.send_message(sender, {
                        'type': 'quiz_response',
                        'status': 'failed',
                        'message': 'Quiz generation failed',
                        'request_id': data.get('request_id', '')
                    })

                    self.logger.context(self.logger.ERROR,
                                      f"Quiz request failed for {sender}")
            else:
                error_msg = "No source text in quiz request"
                self.logger.context(self.logger.WARN, error_msg)
                self.send_message(sender, {
                    'type': 'quiz_response',
                    'status': 'failed',
                    'message': error_msg,
                    'request_id': data.get('request_id', '')
                })

        except Exception as e:
            error_msg = f"Failed to handle quiz request: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'quiz_response',
                'status': 'failed',
                'message': error_msg,
                'request_id': data.get('request_id', '')
            })

    def handle_text_data(self, sender, data):
        """处理文本数据（从其他插件接收文本作为源文本）"""
        try:
            text = data.get('content', '')
            source = data.get('source', 'unknown')

            if text and hasattr(self.ui, 'textEditSource'):
                # 设置为只读
                self.ui.textEditSource.setReadOnly(False)
                self.ui.textEditSource.setPlainText(text)
                self.ui.textEditSource.setReadOnly(True)
                self.current_source_text = text

                comment = f"\n\n--- Source: {sender} ({source}) ---\n"
                current_text = self.ui.textEditSource.toPlainText()
                if not current_text.endswith(comment):
                    self.ui.textEditSource.append(comment)

                self.logger.context(self.logger.INFO,
                                  f"Text data received from {sender}: {len(text)} characters")

                self.send_message(sender, {
                    'type': 'text_received',
                    'status': 'success',
                    'message': 'Text received for quiz generation'
                })
            else:
                self.logger.context(self.logger.WARN,
                                  f"Received empty text from {sender}")

        except Exception as e:
            error_msg = f"Failed to handle text data: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)

    def cleanup(self):
        """清理插件资源"""
        try:
            self.current_source_text = ""
            self.quiz_data = None
            self.current_styles = None

            super().cleanup()

            self.logger.context(self.logger.INFO, "Quiz plugin cleanup complete")

        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Error during cleanup: {str(e)}")