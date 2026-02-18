"""
文本编辑器插件 - 优化版
功能：文本编辑、样式管理、批注系统
"""

import sys
import os
import json
from datetime import datetime

from plugins.learn.editor.annotation import AnnotationManager

try:
    from PyQt6.QtWidgets import QAction
except ImportError:
    from PyQt6.QtGui import QAction

from PyQt6.QtWidgets import (
    QToolBar, QVBoxLayout, QFileDialog, QMessageBox, QColorDialog, QFontDialog, QToolButton
)
from PyQt6.QtGui import (
    QTextCharFormat, QFont, QTextCursor, QColor, QKeySequence
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.uic import loadUi

# 添加路径以便导入base_plugin
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from plugins.base_plugin import BasePlugin
from common.ieltsLog import Logger


class StylePreserver:
    """样式保存和恢复器"""
    
    def __init__(self, text_edit, logger: Logger):
        self.text_edit = text_edit
        self.temp_styles = {}
        self.logger = logger
        
    def extract_styles(self):
        """从文本编辑器中提取样式信息（优化版）"""
        try:
            self.logger.context(self.logger.DEBUG, "Starting to extract styles (optimized)...")
            doc = self.text_edit.document()
            styles = []
            
            # 获取文本编辑器的默认背景色
            default_background = self.text_edit.palette().color(self.text_edit.backgroundRole())
            if not default_background.isValid():
                default_background = QColor("#FFFFFF")  # 白色
            
            # 使用逐字符遍历以确保准确性
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            
            current_style = None
            style_start = -1
            style_end = -1
            current_char_format = None
            
            # 逐字符遍历文档
            char_count = 0
            while not cursor.atEnd():
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, 
                                   QTextCursor.MoveMode.KeepAnchor)
                if cursor.hasSelection():
                    char_format = cursor.charFormat()
                    
                    # 检查是否有任何样式属性
                    has_style = (
                        char_format.fontWeight() > QFont.Weight.Normal or 
                        char_format.fontItalic() or 
                        char_format.fontUnderline() or 
                        char_format.fontStrikeOut()
                    )
                    
                    # 检查前景色
                    current_foreground = char_format.foreground().color()
                    has_color = (current_foreground.isValid() and 
                                not self._colors_equal(current_foreground, QColor("#000000")))
                    
                    # 检查背景色
                    current_background = char_format.background().color()
                    has_background = False
                    if current_background.isValid():
                        # 背景色有效且不是完全透明且不是默认背景色
                        if (current_background.alpha() > 0 and 
                            not self._colors_equal(current_background, default_background) and
                            not self._colors_equal(current_background, QColor("#000000"))):
                            has_background = True
                    
                    # 如果没有任何样式，跳过
                    if not (has_style or has_color or has_background):
                        if current_style is not None and style_start >= 0:
                            style_info = self._create_style_info(current_char_format, style_start, style_end)
                            if style_info:  # 只保存有意义的样式
                                styles.append(style_info)
                            current_style = None
                            current_char_format = None
                            style_start = -1
                        cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                           QTextCursor.MoveMode.MoveAnchor)
                        char_count += 1
                        continue
                    
                    # 如果当前样式为空或与之前样式不同，开始新样式
                    if (current_style is None or 
                        not self._compare_char_formats(current_char_format, char_format)):
                        
                        # 保存上一个样式（如果有）
                        if current_style is not None and style_start >= 0:
                            style_info = self._create_style_info(current_char_format, style_start, style_end)
                            if style_info:  # 只保存有意义的样式
                                styles.append(style_info)
                        
                        # 开始新样式
                        current_style = char_format
                        current_char_format = char_format
                        style_start = cursor.selectionStart()
                        style_end = cursor.selectionEnd()
                    else:
                        # 相同样式，扩展结束位置
                        style_end = cursor.selectionEnd()
                    
                    cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                       QTextCursor.MoveMode.MoveAnchor)
                    char_count += 1
                else:
                    break
            
            # 保存最后一个样式（如果有）
            if current_style is not None and style_start >= 0:
                style_info = self._create_style_info(current_char_format, style_start, style_end)
                if style_info:  # 只保存有意义的样式
                    styles.append(style_info)
            
            self.logger.context(self.logger.DEBUG, f"Extracted {len(styles)} style blocks from {char_count} characters")
            return styles
            
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to extract styles: {e}")
            return []
            
    def _colors_equal(self, color1, color2):
        """比较两个颜色是否相等，考虑透明度和RGB值"""
        if not color1.isValid() and not color2.isValid():
            return True
        if not color1.isValid() or not color2.isValid():
            return False
        
        # 比较RGB和透明度
        return (color1.red() == color2.red() and
                color1.green() == color2.green() and
                color1.blue() == color2.blue() and
                color1.alpha() == color2.alpha())
    
    def _compare_char_formats(self, fmt1, fmt2):
        """比较两个字符格式是否相同"""
        if fmt1 is None or fmt2 is None:
            return fmt1 == fmt2
        
        # 比较字体样式
        font_style_equal = (
            fmt1.fontWeight() == fmt2.fontWeight() and
            fmt1.fontItalic() == fmt2.fontItalic() and
            fmt1.fontUnderline() == fmt2.fontUnderline() and
            fmt1.fontStrikeOut() == fmt2.fontStrikeOut()
        )
        
        # 比较前景色
        fg_equal = self._colors_equal(fmt1.foreground().color(), fmt2.foreground().color())
        
        # 比较背景色
        bg_equal = self._colors_equal(fmt1.background().color(), fmt2.background().color())
        
        return font_style_equal and fg_equal and bg_equal
    
    def _create_style_info(self, char_format, start, end):
        """创建样式信息字典，只保存有意义的样式"""
        if char_format is None:
            return None
            
        style_info = {
            'start': start,
            'end': end,
            'bold': char_format.fontWeight() > QFont.Weight.Normal,
            'italic': char_format.fontItalic(),
            'underline': char_format.fontUnderline(),
            'strikethrough': char_format.fontStrikeOut(),
        }
        
        # 只保存非默认前景色
        default_foreground = QColor("#000000")
        current_foreground = char_format.foreground().color()
        if (current_foreground.isValid() and 
            not self._colors_equal(current_foreground, default_foreground)):
            style_info['color'] = current_foreground.name()
        
        # 只保存非透明且非黑色的背景色
        current_background = char_format.background().color()
        if current_background.isValid():
            # 检查背景色是否不是完全透明且不是黑色
            if (current_background.alpha() > 0 and 
                not self._colors_equal(current_background, QColor("#000000"))):
                style_info['background'] = current_background.name()
        
        # 只有当有实际样式变化时才返回
        if (style_info.get('bold') or 
            style_info.get('italic') or 
            style_info.get('underline') or 
            style_info.get('strikethrough') or
            'color' in style_info or
            'background' in style_info):
            return style_info
        
        return None
            
    def save_styles(self, file_path, annotations=None):
        """保存样式和批注到JSON文件"""
        try:
            self.logger.context(self.logger.INFO, f"Saving styles to: {file_path}")
            styles = self.extract_styles()
            
            self.logger.context(self.logger.DEBUG, f"Extracted {len(styles)} style blocks")
            
            styles_data = {
                'version': '2.1',  # 更新版本号
                'styles': styles,
                'annotations': annotations if annotations else [],
                'timestamp': datetime.now().isoformat(),
                'optimized': True
            }
            
            styles_file = f"{file_path}.json"
            self.logger.context(self.logger.DEBUG, f"Preparing to write JSON file: {styles_file}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(styles_file)), exist_ok=True)
            
            with open(styles_file, 'w', encoding='utf-8') as f:
                json.dump(styles_data, f, ensure_ascii=False, indent=2)
                
            self.logger.context(self.logger.INFO, f"Styles saved successfully: {styles_file}")
            return True
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to save styles: {e}")
            return False
            
    def load_styles(self, file_path):
        """从JSON文件加载样式和批注"""
        try:
            styles_file = f"{file_path}.json"
            self.logger.context(self.logger.DEBUG, f"Attempting to load style file: {styles_file}")
            
            if not os.path.exists(styles_file):
                self.logger.context(self.logger.WARN, f"Style file does not exist: {styles_file}")
                return {'styles': [], 'annotations': []}
            
            self.logger.context(self.logger.INFO, f"Loading style file: {styles_file}")
            with open(styles_file, 'r', encoding='utf-8') as f:
                styles_data = json.load(f)
            
            # 检查是否为优化后的版本
            if styles_data.get('version') == '2.1' and styles_data.get('optimized'):
                self.logger.context(self.logger.DEBUG, "Loading optimized style data")
            else:
                self.logger.context(self.logger.DEBUG, "Loading legacy style data")
            
            styles = styles_data.get('styles', [])
            self.logger.context(self.logger.DEBUG, f"Read {len(styles)} style blocks")
            
            # 应用样式
            style_count = 0
            for style_info in styles:
                try:
                    self.apply_style(style_info)
                    style_count += 1
                except Exception as e:
                    self.logger.context(self.logger.ERROR, f"Failed to apply style: {e}")
            
            self.logger.context(self.logger.INFO, f"Loaded {style_count} style blocks and {len(styles_data.get('annotations', []))} annotations")
            return styles_data
        except json.JSONDecodeError as e:
            self.logger.context(self.logger.ERROR, f"JSON parsing error: {e}")
            return {'styles': [], 'annotations': []}
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to load styles: {e}")
            return {'styles': [], 'annotations': []}
            
    def apply_style(self, style_info):
        """应用单个样式"""
        try:
            cursor = QTextCursor(self.text_edit.document())
            start = style_info['start']
            end = style_info['end']
            
            # 确保位置有效
            if start < 0 or end <= start:
                return
                
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            
            char_format = QTextCharFormat()
            
            # 应用字体样式
            if style_info.get('bold'):
                char_format.setFontWeight(QFont.Weight.Bold)
            
            if style_info.get('italic'):
                char_format.setFontItalic(True)
            
            if style_info.get('underline'):
                char_format.setFontUnderline(True)
            
            if style_info.get('strikethrough'):
                char_format.setFontStrikeOut(True)
            
            # 应用前景色（只有在样式中有指定时才应用）
            color_str = style_info.get('color')
            if color_str:
                color = QColor(color_str)
                if color.isValid() and color_str != "#000000":
                    char_format.setForeground(color)
            
            # 应用背景色（只有在样式中有指定且不是黑色时才应用）
            bg_str = style_info.get('background')
            if bg_str and bg_str != "#000000":
                bg_color = QColor(bg_str)
                if bg_color.isValid() and bg_color.alpha() > 0:
                    char_format.setBackground(bg_color)
            
            # 合并格式
            cursor.mergeCharFormat(char_format)
            
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to apply style: {e}")

class EditorPlugin(BasePlugin):
    """文本编辑器插件（优化版）"""
    
    def __init__(self, plugin_name, ui_file, signal_bus):
        super().__init__(plugin_name, ui_file, signal_bus)
        
        self.current_file = None
        self.is_modified = False
        self.annotation_manager = None
        self.style_preserver = None
        self.auto_save_timer = None
        self.format_actions = {}
        
        # 全局样式设置
        self.current_font = QFont("Arial", 11)
        self.current_text_color = QColor("#000000")
        self.current_bg_color = QColor("#FFFFFF")
        
        self.logger.context(self.logger.INFO, f"Editor plugin created with UI: {ui_file}")

    def on_message(self, sender, data):
        """接收来自其他插件的消息"""
        try:
            message_type = data.get('type', '')
            
            if message_type == 'text_data':
                self.handle_text_data(sender, data)
            
            elif message_type == 'status_query':
                status_info = {
                    'type': 'status_response',
                    'plugin': self.plugin_name,
                    'status': 'running',
                    'file': self.current_file,
                    'modified': self.is_modified,
                    'storage_format': 'Separated storage (TXT + JSON)'
                }
                self.send_message(sender, status_info)
                
        except Exception as e:
            error_msg = f"Error handling message from {sender}: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            
    def initialize(self):
        """初始化插件"""
        try:
            self.logger.context(self.logger.INFO, "Starting editor plugin initialization")
            
            if not self.load_ui():
                self.logger.context(self.logger.ERROR, "Failed to load editor UI")
                return
            
            self.create_toolbar()
            self.connect_text_edit_signals()
            
            self.style_preserver = StylePreserver(self.ui.textEdit, self.logger)
            self.annotation_manager = AnnotationManager(self.ui.textEdit, self)
            
            # 修改：设置默认批注颜色
            if self.annotation_manager:
                self.annotation_manager.set_annotation_color('#FFFFC8')  # 浅黄色
            
            self.setup_initial_state()
            self.setup_auto_save()
            
            self.send_message("main_window", {
                'type': 'status',
                'message': f'{self.plugin_name} plugin initialized'
            })
            
            self.logger.context(self.logger.INFO, "Editor plugin initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize editor plugin: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message("main_window", {
                'type': 'status',
                'message': f'Editor plugin initialization failed: {str(e)}'
            })
    
    def create_toolbar(self):
        """创建工具栏"""
        try:
            if not hasattr(self.ui, 'mainToolbar'):
                toolbar_layout = QVBoxLayout()
                
                self.ui.mainToolbar = QToolBar()
                self.ui.mainToolbar.setObjectName("mainToolbar")
                self.ui.mainToolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                self.ui.mainToolbar.setMovable(False)
                
                self.ui.formatToolbar = QToolBar()
                self.ui.formatToolbar.setObjectName("formatToolbar")
                self.ui.formatToolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
                
                toolbar_layout.addWidget(self.ui.mainToolbar)
                toolbar_layout.addWidget(self.ui.formatToolbar)
                
                main_layout = self.widget.layout()
                if main_layout:
                    main_layout.insertLayout(0, toolbar_layout)
            
            self.ui.mainToolbar.clear()
            if hasattr(self.ui, 'formatToolbar'):
                self.ui.formatToolbar.clear()
            
            self.create_file_actions()
            self.create_edit_actions()
            self.create_format_actions()
            self.create_annotation_actions()
            
            self.ui.mainToolbar.addSeparator()
            
            # 字体设置按钮
            font_btn = QToolButton()
            font_btn.setText("A")
            font_btn.setToolTip("Font Settings")
            font_btn.clicked.connect(self.show_font_dialog)
            self.ui.mainToolbar.addWidget(font_btn)
            
            # 文本颜色按钮
            text_color_btn = QToolButton()
            text_color_btn.setText("🎨")
            text_color_btn.setToolTip("Text Color (Global)")
            text_color_btn.clicked.connect(self.set_global_text_color)
            self.ui.mainToolbar.addWidget(text_color_btn)
            
            # 应用文本颜色到选中文本按钮
            apply_text_color_btn = QToolButton()
            apply_text_color_btn.setText("T")
            apply_text_color_btn.setToolTip("Apply Text Color to Selection")
            apply_text_color_btn.clicked.connect(self.apply_text_color_to_selection)
            self.ui.mainToolbar.addWidget(apply_text_color_btn)
            
            # 背景颜色按钮
            bg_color_btn = QToolButton()
            bg_color_btn.setText("🖍")
            bg_color_btn.setToolTip("Background Color (Global)")
            bg_color_btn.clicked.connect(self.set_global_background_color)
            self.ui.mainToolbar.addWidget(bg_color_btn)
            
            # 应用背景颜色到选中文本按钮
            apply_bg_color_btn = QToolButton()
            apply_bg_color_btn.setText("B")
            apply_bg_color_btn.setToolTip("Apply Background Color to Selection")
            apply_bg_color_btn.clicked.connect(self.apply_background_color_to_selection)
            self.ui.mainToolbar.addWidget(apply_bg_color_btn)
            
        except Exception as e:
            error_msg = f"Failed to create toolbar: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def show_font_dialog(self):
        """显示字体设置对话框"""
        self.logger.context(self.logger.DEBUG, "Opening font dialog")
        font, ok = QFontDialog.getFont(self.current_font, self.widget, "Font Settings")
        if ok:
            self.current_font = font
            if hasattr(self.ui, 'textEdit'):
                self.ui.textEdit.setFont(font)
                self.is_modified = True
                self.update_status_bar("Font updated")
                self.logger.context(self.logger.INFO, f"Font updated to: {font.family()}, size: {font.pointSize()}")
    
    def set_global_text_color(self):
        """设置全局文本颜色"""
        self.logger.context(self.logger.DEBUG, "Setting global text color")
        color = QColorDialog.getColor(self.current_text_color, self.widget, "Text Color")
        if color.isValid():
            self.current_text_color = color
            self.update_status_bar(f"Text color set to {color.name()}")
            self.logger.context(self.logger.INFO, f"Text color set to: {color.name()}")
    
    def set_global_background_color(self):
        """设置全局背景颜色"""
        self.logger.context(self.logger.DEBUG, "Setting global background color")
        color = QColorDialog.getColor(self.current_bg_color, self.widget, "Background Color")
        if color.isValid():
            self.current_bg_color = color
            self.update_status_bar(f"Background color set to {color.name()}")
            self.logger.context(self.logger.INFO, f"Background color set to: {color.name()}")
    
    def apply_text_color_to_selection(self):
        """将当前文本颜色应用到选中文本"""
        if not hasattr(self.ui, 'textEdit'):
            return
        
        cursor = self.ui.textEdit.textCursor()
        if cursor.hasSelection():
            text_format = QTextCharFormat()
            text_format.setForeground(self.current_text_color)
            cursor.mergeCharFormat(text_format)
            self.is_modified = True
            self.update_status_bar("Text color applied to selection")
            self.logger.context(self.logger.DEBUG, "Text color applied to selected text")
        else:
            QMessageBox.information(self.widget, "Info", "Select text first")
    
    def apply_background_color_to_selection(self):
        """将当前背景颜色应用到选中文本"""
        if not hasattr(self.ui, 'textEdit'):
            return
        
        cursor = self.ui.textEdit.textCursor()
        if cursor.hasSelection():
            text_format = QTextCharFormat()
            text_format.setBackground(self.current_bg_color)
            cursor.mergeCharFormat(text_format)
            self.is_modified = True
            self.update_status_bar("Background color applied to selection")
            self.logger.context(self.logger.DEBUG, "Background color applied to selected text")
        else:
            QMessageBox.information(self.widget, "Info", "Select text first")
    
    def create_file_actions(self):
        """创建文件操作动作"""
        file_actions = [
            ("📄", "Ctrl+N", "New document", self.new_file),
            ("📂", "Ctrl+O", "Open file", self.open_file),
            ("💾", "Ctrl+S", "Save file", self.save_file),
            ("💾+", "Ctrl+Shift+S", "Save as", self.save_file_as),
            ("🧹", "Ctrl+Del", "Clear all", self.clear_current_text),
            # 新增：PDF 导出按钮
            ("📄->📘", "Ctrl+P", "Export to PDF", self.export_to_pdf)
        ]
        
        for icon, shortcut, tooltip, slot in file_actions:
            action = self.create_action(icon, shortcut, tooltip, slot)
            self.ui.mainToolbar.addAction(action)
    
    def export_to_pdf(self):
        """将文本导出为 PDF"""
        if not hasattr(self.ui, 'textEdit'):
            QMessageBox.warning(self.widget, "Warning", "Text editor not available")
            return
        
        # 获取文本内容
        text = self.ui.textEdit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self.widget, "Warning", "No text to export")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self.widget, "Export to PDF", "", 
            "PDF files (*.pdf);;All files (*.*)"
        )
        
        if not file_path:
            return  # 用户取消了保存
        
        # 确保文件以 .pdf 结尾
        if not file_path.endswith('.pdf'):
            file_path += '.pdf'
        
        try:
            self.logger.context(self.logger.INFO, f"Exporting to PDF: {file_path}")
            
            # 使用 QTextDocument 创建 PDF
            from PyQt6.QtGui import QTextDocument
            from PyQt6.QtPrintSupport import QPrinter
            
            # 创建打印机对象
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            
            # 创建文档
            document = QTextDocument()
            
            # 设置文档内容，保留基本格式
            if hasattr(self.ui.textEdit, 'toHtml'):
                html_content = self.ui.textEdit.toHtml()
                document.setHtml(html_content)
            else:
                # 如果无法获取 HTML，使用纯文本
                document.setPlainText(text)
            
            # 设置文档字体
            document.setDefaultFont(self.current_font)
            
            # 设置文档的页边距（单位：像素）
            document.setDocumentMargin(40)  # 40像素的页边距
            
            # 打印到 PDF
            document.print(printer)
            
            self.update_status_bar(f"Exported to PDF: {os.path.basename(file_path)}")
            QMessageBox.information(self.widget, "Success", 
                                f"PDF exported successfully!\n\nSaved to:\n{file_path}")
            self.logger.context(self.logger.INFO, "PDF export completed")
            
        except ImportError as e:
            error_msg = f"PDF export requires PyQt6 printing support: {str(e)}"
            QMessageBox.critical(self.widget, "Error", error_msg)
            self.logger.context(self.logger.ERROR, error_msg)
            import traceback
            traceback.print_exc()
        except Exception as e:
            error_msg = f"Failed to export PDF: {str(e)}"
            QMessageBox.critical(self.widget, "Error", error_msg)
            self.logger.context(self.logger.ERROR, error_msg)
            import traceback
            traceback.print_exc()

    def create_edit_actions(self):
        """创建编辑操作动作"""
        edit_actions = [
            ("↶", "Ctrl+Z", "Undo", self.undo),
            ("↷", "Ctrl+Y", "Redo", self.redo),
            ("✂", "Ctrl+X", "Cut", self.cut),
            ("📋", "Ctrl+C", "Copy", self.copy),
            ("📎", "Ctrl+V", "Paste", self.paste),
            ("🔍", "Ctrl+F", "Find", self.find_text),
            ("📝", "Ctrl+A", "Select all", self.select_all)
        ]
        
        for icon, shortcut, tooltip, slot in edit_actions:
            action = self.create_action(icon, shortcut, tooltip, slot)
            self.ui.mainToolbar.addAction(action)
        
    def create_format_actions(self):
        """创建格式操作动作"""
        if not hasattr(self.ui, 'formatToolbar'):
            return
            
        format_actions = [
            ("B", "Ctrl+B", "Bold", self.set_bold, True),
            ("I", "Ctrl+I", "Italic", self.set_italic, True),
            ("U", "Ctrl+U", "Underline", self.set_underline, True),
            ("S", "Ctrl+Shift+S", "Strikethrough", self.set_strikethrough, True)
        ]
        
        for icon, shortcut, tooltip, slot, checkable in format_actions:
            if checkable:
                action = self.create_checkable_action(icon, shortcut, tooltip, slot)
                self.format_actions[tooltip] = action
            else:
                action = self.create_action(icon, shortcut, tooltip, slot)
            self.ui.formatToolbar.addAction(action)
    
    def create_annotation_actions(self):
        """创建批注操作动作"""
        annotation_actions = [
            ("📝", "Ctrl+Alt+A", "Add annotation", self.add_annotation),
            ("👁", "Ctrl+Alt+S", "Show annotations", self.show_annotations),
            # 修改：添加批注颜色设置按钮
            ("🎨", "", "Annotation Color", self.show_annotation_color_menu)
        ]
        
        for icon, shortcut, tooltip, slot in annotation_actions:
            action = self.create_action(icon, shortcut, tooltip, slot)
            self.ui.mainToolbar.addAction(action)
    
    def show_annotation_color_menu(self):
        """显示批注颜色选择菜单"""
        if self.annotation_manager:
            # 获取工具栏按钮的位置
            toolbar = self.ui.mainToolbar
            actions = toolbar.actions()
            color_action = None
            
            # 找到颜色设置动作
            for action in actions:
                if action.text() == "🎨" or action.toolTip() == "Annotation Color":
                    color_action = action
                    break
            
            if color_action:
                # 获取按钮位置
                button = toolbar.widgetForAction(color_action)
                if button:
                    pos = button.mapToGlobal(button.rect().bottomLeft())
                    self.annotation_manager.show_color_menu(pos)
            else:
                # 如果找不到按钮，显示在鼠标位置
                pos = self.widget.mapToGlobal(self.widget.rect().center())
                self.annotation_manager.show_color_menu(pos)
    
    def create_action(self, icon, shortcut, tooltip, slot):
        """创建动作的辅助方法"""
        action = QAction(icon, self.widget)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if tooltip:
            action.setToolTip(tooltip)
        action.triggered.connect(slot)
        return action
    
    def create_checkable_action(self, icon, shortcut, tooltip, slot):
        """创建可选中动作的辅助方法"""
        action = QAction(icon, self.widget)
        action.setCheckable(True)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if tooltip:
            action.setToolTip(tooltip)
        action.triggered.connect(slot)
        return action
    
    def connect_text_edit_signals(self):
        """连接文本编辑器的信号"""
        if hasattr(self.ui, 'textEdit'):
            self.ui.textEdit.textChanged.connect(self.on_text_changed)
            self.ui.textEdit.cursorPositionChanged.connect(self.update_format_actions)
            self.ui.textEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.ui.textEdit.customContextMenuRequested.connect(self.show_context_menu)
            self.logger.context(self.logger.DEBUG, "Text editor signals connected")
    
    def setup_auto_save(self):
        """设置自动保存"""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(60000)  # 60秒
        self.logger.context(self.logger.DEBUG, "Auto-save timer set up")
    
    def auto_save(self):
        """自动保存"""
        if self.is_modified and hasattr(self.ui, 'textEdit'):
            self.logger.context(self.logger.DEBUG, "Auto-saving")
    
    def setup_initial_state(self):
        """设置初始状态"""
        try:
            self.update_status_bar()
            self.logger.context(self.logger.DEBUG, "Initial state set up")
            
        except Exception as e:
            error_msg = f"Failed to set up initial state: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    # ==================== 基本编辑方法 ====================
    
    def on_text_changed(self):
        """文本改变时触发"""
        self.is_modified = True
        self.update_status_bar()
    
    def undo(self):
        """撤销"""
        if hasattr(self.ui, 'textEdit'):
            self.ui.textEdit.undo()
    
    def redo(self):
        """重做"""
        if hasattr(self.ui, 'textEdit'):
            self.ui.textEdit.redo()
    
    def cut(self):
        """剪切"""
        if hasattr(self.ui, 'textEdit'):
            self.ui.textEdit.cut()
    
    def copy(self):
        """复制"""
        if hasattr(self.ui, 'textEdit'):
            self.ui.textEdit.copy()
    
    def paste(self):
        """粘贴"""
        if hasattr(self.ui, 'textEdit'):
            self.ui.textEdit.paste()
    
    def find_text(self):
        """查找文本"""
        QMessageBox.information(self.widget, "Info", "Find function - under development")
    
    def select_all(self):
        """全选文本"""
        if hasattr(self.ui, 'textEdit'):
            self.ui.textEdit.selectAll()
    
    def set_bold(self):
        """设置粗体"""
        if hasattr(self.ui, 'textEdit'):
            cursor = self.ui.textEdit.textCursor()
            if cursor.hasSelection():
                text_format = QTextCharFormat()
                text_format.setFontWeight(
                    QFont.Weight.Bold if not cursor.charFormat().fontWeight() == QFont.Weight.Bold 
                    else QFont.Weight.Normal
                )
                cursor.mergeCharFormat(text_format)
                self.is_modified = True
                self.logger.context(self.logger.DEBUG, "Bold toggled")
            else:
                QMessageBox.information(self.widget, "Info", "Select text first")
    
    def set_italic(self):
        """设置斜体"""
        if hasattr(self.ui, 'textEdit'):
            cursor = self.ui.textEdit.textCursor()
            if cursor.hasSelection():
                text_format = QTextCharFormat()
                text_format.setFontItalic(not cursor.charFormat().fontItalic())
                cursor.mergeCharFormat(text_format)
                self.is_modified = True
                self.logger.context(self.logger.DEBUG, "Italic toggled")
            else:
                QMessageBox.information(self.widget, "Info", "Select text first")
    
    def set_underline(self):
        """设置下划线"""
        if hasattr(self.ui, 'textEdit'):
            cursor = self.ui.textEdit.textCursor()
            if cursor.hasSelection():
                text_format = QTextCharFormat()
                text_format.setFontUnderline(not cursor.charFormat().fontUnderline())
                cursor.mergeCharFormat(text_format)
                self.is_modified = True
                self.logger.context(self.logger.DEBUG, "Underline toggled")
            else:
                QMessageBox.information(self.widget, "Info", "Select text first")
    
    def set_strikethrough(self):
        """设置删除线"""
        if hasattr(self.ui, 'textEdit'):
            cursor = self.ui.textEdit.textCursor()
            if cursor.hasSelection():
                text_format = QTextCharFormat()
                text_format.setFontStrikeOut(not cursor.charFormat().fontStrikeOut())
                cursor.mergeCharFormat(text_format)
                self.is_modified = True
            else:
                QMessageBox.information(self.widget, "Info", "Select text first")
    
    def clear_current_text(self):
        """清除当前文本"""
        if hasattr(self.ui, 'textEdit'):
            reply = QMessageBox.question(
                self.widget, "Confirm",
                "Clear current text?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.ui.textEdit.clear()
                if self.annotation_manager:
                    self.annotation_manager.annotations.clear()
                self.is_modified = True
                self.update_status_bar("Text cleared")
                self.logger.context(self.logger.INFO, "Text cleared")
    
    def update_format_actions(self):
        """更新格式动作状态"""
        if not hasattr(self.ui, 'textEdit'):
            return
        
        cursor = self.ui.textEdit.textCursor()
        char_format = cursor.charFormat()
        
        if 'Bold' in self.format_actions:
            self.format_actions['Bold'].setChecked(char_format.fontWeight() == QFont.Weight.Bold)
        
        if 'Italic' in self.format_actions:
            self.format_actions['Italic'].setChecked(char_format.fontItalic())
        
        if 'Underline' in self.format_actions:
            self.format_actions['Underline'].setChecked(char_format.fontUnderline())
        
        if 'Strikethrough' in self.format_actions:
            self.format_actions['Strikethrough'].setChecked(char_format.fontStrikeOut())
    
    def show_context_menu(self, position):
        """显示上下文菜单"""
        if not hasattr(self.ui, 'textEdit'):
            return
        
        menu = self.ui.textEdit.createStandardContextMenu()
        
        menu.addSeparator()
        format_menu = menu.addMenu("🎨 Format")
        
        # ... 格式菜单项保持不变 ...
        
        if self.annotation_manager:
            menu.addSeparator()
            annotation_menu = menu.addMenu("📝 Annotation")
            
            add_annotation_action = QAction("Add Annotation", self.widget)
            add_annotation_action.triggered.connect(self.add_annotation)
            annotation_menu.addAction(add_annotation_action)
            
            # 修改：添加批注颜色设置选项
            color_menu = annotation_menu.addMenu("Set Annotation Color")
            
            # 添加颜色选项
            for i, color in enumerate(self.annotation_manager.annotation_colors):
                color_action = QAction(f"Color {i+1}", self.widget)
                
                # 创建带颜色的图标
                try:
                    from PyQt6.QtGui import QPixmap, QIcon
                    icon_pixmap = QPixmap(16, 16)
                    icon_pixmap.fill(QColor(color))
                    color_action.setIcon(QIcon(icon_pixmap))
                except:
                    pass
                
                # 连接信号
                if color == self.annotation_manager.get_annotation_color():
                    color_action.setCheckable(True)
                    color_action.setChecked(True)
                
                color_action.triggered.connect(lambda checked, c=color: self.annotation_manager.set_annotation_color(c) if self.annotation_manager else None)
                color_menu.addAction(color_action)
            
            # 添加自定义颜色选项
            color_menu.addSeparator()
            custom_color_action = QAction("Custom Color...", self.widget)
            custom_color_action.triggered.connect(self.annotation_manager.choose_custom_color)
            color_menu.addAction(custom_color_action)
            
            # 显示当前批注颜色
            annotation_menu.addSeparator()
            current_color_action = QAction(f"Current: {self.annotation_manager.get_annotation_color()}", self.widget)
            current_color_action.setEnabled(False)
            annotation_menu.addAction(current_color_action)
        
            menu.exec(self.ui.textEdit.viewport().mapToGlobal(position))
    
    def update_status_bar(self, message=None):
        """更新状态栏信息"""
        if not hasattr(self.ui, 'statusBar'):
            return
        
        if message:
            self.ui.statusBar.showMessage(message, 3000)
        elif hasattr(self.ui, 'textEdit'):
            text = self.ui.textEdit.toPlainText()
            lines = text.count('\n') + 1
            words = len(text.split())
            chars = len(text)
            
            file_info = ""
            if self.current_file:
                file_info = f" | File: {os.path.basename(self.current_file)}"
            
            annotation_info = ""
            if self.annotation_manager:
                annotation_info = f" | Annotations: {len(self.annotation_manager.annotations)}"
            
            # 修改：添加批注颜色信息
            color_info = ""
            if self.annotation_manager:
                color = self.annotation_manager.get_annotation_color()
                color_info = f" | Annotation Color: {color}"
            
            status_text = f"Lines: {lines} | Words: {words} | Chars: {chars}{file_info}{annotation_info}{color_info}"
            self.ui.statusBar.showMessage(status_text)
    
    # ==================== 文件操作方法 ====================
    
    def new_file(self):
        """创建新文件"""
        self.logger.context(self.logger.DEBUG, "Creating new file")
        if self.check_save():
            self.ui.textEdit.clear()
            self.current_file = None
            self.is_modified = False
            if self.annotation_manager:
                self.annotation_manager.annotations.clear()
            
            self.current_font = QFont("Arial", 11)
            self.ui.textEdit.setFont(self.current_font)
            
            self.update_status_bar("New document created")
            self.logger.context(self.logger.INFO, "New document created")
    
    def open_file(self):
        """打开文件"""
        self.logger.context(self.logger.DEBUG, "Opening file")
        if self.check_save():
            file_path, _ = QFileDialog.getOpenFileName(
                self.widget, "Open File", "", 
                "Text files (*.txt);;All files (*.*)"
            )
            
            if file_path:
                self.load_file(file_path)
    
    def load_file(self, file_path):
        """加载文件"""
        try:
            self.logger.context(self.logger.INFO, f"Loading file: {file_path}")
            
            # 先加载文本内容
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # 设置文本内容
            self.ui.textEdit.setPlainText(content)
            self.current_file = file_path
            self.is_modified = False
            
            self.logger.context(self.logger.DEBUG, "Text content loaded")
            
            # 延迟加载样式，确保文本已加载完成
            QTimer.singleShot(100, lambda: self.load_styles_delayed(file_path))
            
            self.update_status_bar(f"File opened: {os.path.basename(file_path)}")
            
        except Exception as e:
            error_msg = f"Cannot open file: {str(e)}"
            QMessageBox.critical(self.widget, "Error", error_msg)
            self.logger.context(self.logger.ERROR, error_msg)
    
    def load_styles_delayed(self, file_path):
        """延迟加载样式"""
        try:
            self.logger.context(self.logger.DEBUG, f"Delayed loading styles: {file_path}")
            if self.style_preserver:
                styles_data = self.style_preserver.load_styles(file_path)
                
                if self.annotation_manager and 'annotations' in styles_data:
                    self.annotation_manager.load_annotations_from_list(styles_data['annotations'])
                
                self.logger.context(self.logger.INFO, f"Styles loaded: {file_path}")
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to load styles: {e}")
    
    def save_file(self):
        """保存文件"""
        self.logger.context(self.logger.DEBUG, "Saving file")
        if self.current_file:
            success = self.save_to_file(self.current_file)
            if success:
                self.update_status_bar(f"File saved: {os.path.basename(self.current_file)}")
        else:
            self.save_file_as()
    
    def save_file_as(self):
        """另存文件"""
        self.logger.context(self.logger.DEBUG, "Saving file as")
        file_path, _ = QFileDialog.getSaveFileName(
            self.widget, "Save As", "", 
            "Text files (*.txt);;All files (*.*)"
        )
        
        if file_path:
            if not file_path.endswith('.txt'):
                file_path += '.txt'
                
            if self.save_to_file(file_path):
                self.current_file = file_path
                self.update_status_bar(f"File saved: {os.path.basename(file_path)}")
    
    def save_to_file(self, file_path):
        """保存内容到文件"""
        try:
            self.logger.context(self.logger.INFO, f"Starting to save file: {file_path}")
            
            if not hasattr(self.ui, 'textEdit'):
                self.logger.context(self.logger.ERROR, "textEdit attribute does not exist")
                return False
            
            # 1. 保存文本内容
            self.logger.context(self.logger.DEBUG, "Saving text content")
            content = self.ui.textEdit.toPlainText()
            
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            self.logger.context(self.logger.DEBUG, f"Text content saved to: {file_path}")
            
            # 2. 保存样式和批注
            if self.annotation_manager:
                annotations = self.annotation_manager.get_annotations_list()
                self.logger.context(self.logger.DEBUG, f"Preparing to save {len(annotations)} annotations")
            else:
                annotations = []
                self.logger.context(self.logger.WARN, "Annotation manager not initialized")
            
            # 确保样式保存器已初始化
            if not self.style_preserver:
                self.logger.context(self.logger.WARN, "Style preserver not initialized, creating...")
                self.style_preserver = StylePreserver(self.ui.textEdit, self.logger)
            
            # 保存样式
            self.logger.context(self.logger.DEBUG, "Starting to save styles")
            success = self.style_preserver.save_styles(file_path, annotations)
            
            if success:
                self.is_modified = False
                self.logger.context(self.logger.INFO, f"File saved successfully: {file_path}")
                return True
            else:
                self.logger.context(self.logger.WARN, f"Failed to save styles: {file_path}")
                # 即使样式保存失败，文本内容已经保存了
                self.is_modified = False
                return True
                
        except PermissionError as e:
            error_msg = f"Permission denied to save file: {str(e)}"
            QMessageBox.critical(self.widget, "Error", error_msg)
            self.logger.context(self.logger.ERROR, error_msg)
            return False
        except Exception as e:
            error_msg = f"Failed to save file: {str(e)}"
            QMessageBox.critical(self.widget, "Error", error_msg)
            self.logger.context(self.logger.ERROR, error_msg)
            return False
    
    def check_save(self):
        """检查是否需要保存"""
        if self.is_modified:
            reply = QMessageBox.question(
                self.widget, "Save Document",
                "Document modified. Save changes?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                return self.save_file()
            elif reply == QMessageBox.StandardButton.No:
                return True
            else:
                return False
        return True
    
    # ==================== 批注方法 ====================
    
    def add_annotation(self):
        """添加批注"""
        if not hasattr(self.ui, 'textEdit'):
            return
        
        cursor = self.ui.textEdit.textCursor()
        selected_text = cursor.selectedText()
        
        if not selected_text:
            QMessageBox.information(self.widget, "Info", "Select text first")
            return
        
        if self.annotation_manager:
            if self.annotation_manager.add_annotation():
                self.is_modified = True
                self.logger.context(self.logger.INFO, "Annotation added")
                self.update_status_bar("Annotation added")
    
    def show_annotations(self):
        """显示批注"""
        if self.annotation_manager:
            self.annotation_manager.show_annotations_panel()
    
    # ==================== 插件通信方法 ====================
    
    def send_text_to_plugins(self):
        """发送文本到其他插件"""
        if not hasattr(self.ui, 'textEdit'):
            return
        
        text = self.ui.textEdit.toPlainText()
        if text.strip():
            self.broadcast_message({
                'type': 'text_data',
                'source': 'editor',
                'content': text,
                'length': len(text),
                'timestamp': datetime.now().isoformat()
            })
            
            self.send_message("main_window", {
                'type': 'status',
                'message': f'Text broadcast to plugins ({len(text)} chars)'
            })
        else:
            QMessageBox.information(self.widget, "Info", "No text to send")
    
    def handle_text_data(self, sender, data):
        """处理文本数据（从其他插件接收文本）"""
        try:
            text = data.get('content', '')
            source = data.get('source', 'unknown')
            
            if text and hasattr(self.ui, 'textEdit'):
                current_text = self.ui.textEdit.toPlainText()
                if current_text:
                    separator = "\n\n" + "="*60 + "\nFrom " + sender + " (" + source + "):\n" + "="*60 + "\n\n"
                    self.ui.textEdit.append(separator)
                self.ui.textEdit.append(text)
                
                self.ui.textEdit.moveCursor(QTextCursor.MoveOperation.End)
                
                self.update_status_bar()
                
                self.send_message(sender, {
                    'type': 'text_received',
                    'status': 'success',
                    'message': 'Text received and displayed'
                })
                
                self.logger.context(self.logger.INFO, f"Text received from {sender}: {len(text)} chars")
                
        except Exception as e:
            error_msg = f"Failed to handle text data: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    # ==================== 清理方法 ====================
    
    def cleanup(self):
        """清理插件资源"""
        try:
            if self.auto_save_timer:
                self.auto_save_timer.stop()
            
            if self.annotation_manager:
                if self.annotation_manager.display_widget:
                    self.annotation_manager.display_widget.hide()
                self.annotation_manager = None
            
            super().cleanup()
            
            self.logger.context(self.logger.INFO, "Editor plugin cleanup complete")
            
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Error during cleanup: {str(e)}")