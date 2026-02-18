import sys
import os
from datetime import datetime

try:
    from PyQt6.QtWidgets import QAction
except ImportError:
    from PyQt6.QtGui import QAction

from PyQt6.QtWidgets import (
    QWidget, QTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox, QColorDialog,
    QLabel, QDialog, QPushButton, QLineEdit,
    QFrame, QMenu, QApplication, QListWidget, QListWidgetItem, QTextBrowser,
    QGroupBox, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import (
    QTextCharFormat, QTextCursor, QColor, QActionGroup, QPixmap, QIcon
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.uic import loadUi

# 添加路径以便导入base_plugin
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class AnnotationWidget(QFrame):
    """批注显示窗口 - 添加可拖动功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 修改窗口标志，移除透明背景相关设置
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        
        self.annotations = []
        self.current_annotation_index = 0
        
        # 拖动相关变量
        self.dragging = False
        self.drag_position = QPoint()
        
        # 设置固定宽度，确保显示美观
        self.setFixedWidth(350)
        self.setMinimumHeight(300)
        
        # 添加背景色，确保不透明
        self.setStyleSheet("""
            AnnotationWidget {
                background-color: white;
                border: 2px solid #4a6fea;
                border-radius: 15px;
                padding: 3px;
            }
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        
        # 标题栏 - 设置为可拖动区域
        title_bar = QFrame()
        title_bar.setFixedHeight(45)  # 增加高度
        title_bar.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a6fea, stop:1 #2a4fca);
                border-radius: 12px 12px 0 0;
                padding: 5px 10px;
            }
        """)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(5, 5, 5, 5)
        title_layout.setSpacing(15)
        
        # 批注列表标题 - 增加内边距和字体大小
        title_label = QLabel("📝 Annotation List")
        title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: white;
            padding: 5px 0px;
            background-color: transparent;
        """)
        title_label.setMinimumHeight(30)  # 确保文字有足够空间
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(title_label)
        
        # 添加弹性空间，使标题和拖动提示分开
        title_layout.addStretch()
        
        # 添加拖动提示 - 调整字体大小和内边距
        drag_hint = QLabel("↕ Move")
        drag_hint.setStyleSheet("""
            color: rgba(255,255,255,0.95); 
            font-size: 13px; 
            font-weight: normal;
            padding: 5px 12px;
            background-color: rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        """)
        drag_hint.setMinimumWidth(80)  # 增加最小宽度
        drag_hint.setMinimumHeight(26)  # 设置最小高度
        drag_hint.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        title_layout.addWidget(drag_hint)
        
        # 添加一些空间
        title_layout.addSpacing(15)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)  # 增大按钮
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-size: 16px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        
        title_bar.setLayout(title_layout)
        main_layout.addWidget(title_bar)
        
        # 导航栏
        nav_frame = QFrame()
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(10)
        
        self.prev_btn = QPushButton("◀ Previous")
        self.next_btn = QPushButton("Next ▶")
        self.count_label = QLabel("0/0")
        self.count_label.setStyleSheet("""
            font-weight: bold; 
            color: white; 
            font-size: 14px;
            padding: 5px 15px;
            background-color: #ff6b6b;
            border-radius: 12px;
            min-height: 24px;
        """)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setMinimumWidth(70)
        
        for btn in [self.prev_btn, self.next_btn]:
            btn.setFixedHeight(36)  # 增加按钮高度
            btn.setMinimumWidth(90)  # 设置最小宽度确保文字完整显示
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4a6fea;
                    border: 1px solid #3a5fda;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-size: 13px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #5b7cfa;
                    border-color: #4a6fea;
                }
                QPushButton:disabled {
                    color: rgba(255,255,255,0.5);
                    background-color: #9ab3ff;
                    border-color: #8aa3ef;
                }
            """)
            
        self.prev_btn.clicked.connect(self.show_previous_annotation)
        self.next_btn.clicked.connect(self.show_next_annotation)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.count_label)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch()
        
        nav_frame.setLayout(nav_layout)
        main_layout.addWidget(nav_frame)
        
        # 批注内容
        self.annotation_content = QTextBrowser()
        self.annotation_content.setStyleSheet("""
            QTextBrowser {
                background-color: #f8f9ff;
                border: 2px solid #c5d3ff;
                border-radius: 12px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        self.annotation_content.setMaximumHeight(200)
        main_layout.addWidget(self.annotation_content)
        
        # 批注列表 - 修改样式以红色和蓝色为主
        self.annotation_list = QListWidget()
        self.annotation_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9ff;
                border: 2px solid #c5d3ff;
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 12px;
                border: 1px solid #e1e8ff;
                border-radius: 10px;
                margin: 3px;
                background-color: white;
            }
            QListWidget::item:selected {
                background-color: #ffeded;
                color: #d63031;
                border: 2px solid #ff6b6b;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background-color: #eef2ff;
                border-color: #a5b8ff;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f3ff;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c5d3ff;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a5b8ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.annotation_list.itemClicked.connect(self.on_annotation_selected)
        
        main_layout.addWidget(self.annotation_list)
        
        # 创建外边框效果（使用两层边框）
        outer_frame = QFrame()
        outer_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #eef2ff;
                border-radius: 13px;
                padding: 0px;
            }
        """)
        
        # 重新组织布局，将现有内容放入外边框
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(10, 10, 10, 10)
        
        # 将原有内容移动到外边框内
        temp_widget = QWidget()
        temp_widget.setLayout(main_layout)
        outer_layout.addWidget(temp_widget)
        
        outer_frame.setLayout(outer_layout)
        
        # 设置最终布局
        final_layout = QVBoxLayout()
        final_layout.setContentsMargins(0, 0, 0, 0)
        final_layout.addWidget(outer_frame)
        self.setLayout(final_layout)
        
        # 添加阴影效果
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(74, 111, 234, 60))
            shadow.setOffset(0, 3)
            self.setGraphicsEffect(shadow)
        except Exception:
            pass
        
        # 设置窗口最小宽度和高度，确保内容不会被裁剪
        self.setMinimumWidth(380)
        self.setMinimumHeight(450)
        # 设置最大高度，防止窗口太高
        self.setMaximumHeight(700)

    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在标题栏区域
            if event.pos().y() <= 50:  # 标题栏高度区域
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                # 更改鼠标光标
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            # 使用 move 方法移动窗口，而不是 setGeometry
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 停止拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            # 恢复鼠标光标
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
    
    def enterEvent(self, event):
        """鼠标进入窗口事件"""
        super().enterEvent(event)
        # 移除动态修改阴影效果的代码，避免窗口重绘问题
    
    def leaveEvent(self, event):
        """鼠标离开窗口事件"""
        super().leaveEvent(event)
        # 移除动态修改阴影效果的代码，避免窗口重绘问题
    
    def set_annotations(self, annotations):
        """设置批注 - 修改颜色显示"""
        self.annotations = annotations
        self.current_annotation_index = 0
        
        self.annotation_list.clear()
        for i, ann in enumerate(annotations):
            selected_text = ann.get('selected_text', '')
            if len(selected_text) > 30:
                selected_text = selected_text[:27] + "..."
            
            author = ann.get('author', 'Anonymous')
            # 简化显示，只显示序号和选中文本
            item_text = f"{i+1}. {selected_text}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            # 使用红蓝交替的颜色方案
            if i % 2 == 0:
                # 偶数项使用蓝色系背景
                item.setBackground(QColor(234, 242, 255))  # 浅蓝色
                item.setForeground(QColor(30, 80, 200))    # 深蓝色文字
            else:
                # 奇数项使用红色系背景
                item.setBackground(QColor(255, 240, 240))  # 浅红色
                item.setForeground(QColor(180, 40, 40))    # 深红色文字
            
            # 为选中项设置不同的背景色
            item.setData(Qt.ItemDataRole.UserRole + 1, i % 2)  # 存储颜色类型
            
            self.annotation_list.addItem(item)
        
        self.update_navigation()
        self.update_display()
    
    def update_display(self):
        """更新显示"""
        if not self.annotations:
            self.annotation_content.setHtml("""
                <div style="color: #888; font-style: italic; text-align: center; padding: 20px;">
                    No annotations
                </div>
            """)
            return
            
        ann = self.annotations[self.current_annotation_index]
        annotation_text = ann.get('text', '').replace('\n', '<br>')
        
        # 根据索引选择红蓝主题
        if self.current_annotation_index % 2 == 0:
            # 蓝色主题
            theme_color = "#4a6fea"
            theme_light = "#eef2ff"
            theme_dark = "#2a4fca"
        else:
            # 红色主题
            theme_color = "#ff6b6b"
            theme_light = "#fff0f0"
            theme_dark = "#d63031"
        
        html = f"""
        <div style="font-family: 'Microsoft YaHei', sans-serif;">
            <div style="background-color: {theme_light}; padding: 8px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid {theme_color};">
                <p style="margin: 0; font-weight: 600; color: {theme_dark}; font-size: 14px;">#{self.current_annotation_index + 1} • {ann.get('author', 'Anonymous')}</p>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">
                    {ann.get('timestamp', '')[:16]}
                </p>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e1e8f0;">
                <p style="margin: 0; font-weight: 600; color: #555; font-size: 13px;">Selected Text:</p>
                <p style="margin: 5px 0 0 5px; font-style: italic; color: #333; font-size: 13px; border-left: 2px solid {theme_color}; padding-left: 10px;">
                    "{ann.get('selected_text', '')}"
                </p>
            </div>
            
            <div style="background-color: white; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e1e8f0;">
                <p style="margin: 0; font-weight: 600; color: #555; font-size: 13px;">Content:</p>
                <p style="margin: 8px 0 0 5px; color: #333; font-size: 13px; line-height: 1.5;">
                    {annotation_text}
                </p>
            </div>
        </div>
        """
        
        self.annotation_content.setHtml(html)
        
        # 更新列表选中项
        for i in range(self.annotation_list.count()):
            item = self.annotation_list.item(i)
            if i == self.current_annotation_index:
                item.setSelected(True)
                # 选中时使用主题色
                color_type = item.data(Qt.ItemDataRole.UserRole + 1)
                if color_type == 0:  # 蓝色主题
                    item.setBackground(QColor(220, 230, 255))
                else:  # 红色主题
                    item.setBackground(QColor(255, 220, 220))
            else:
                item.setSelected(False)

    def update_navigation(self):
        """更新导航状态"""
        count = len(self.annotations)
        self.count_label.setText(f"{self.current_annotation_index + 1}/{count}" if count > 0 else "0/0")
        self.prev_btn.setEnabled(self.current_annotation_index > 0)
        self.next_btn.setEnabled(self.current_annotation_index < count - 1)
    
    def show_previous_annotation(self):
        """显示上一个批注"""
        if self.current_annotation_index > 0:
            self.current_annotation_index -= 1
            self.update_navigation()
            self.update_display()
    
    def show_next_annotation(self):
        """显示下一个批注"""
        if self.current_annotation_index < len(self.annotations) - 1:
            self.current_annotation_index += 1
            self.update_navigation()
            self.update_display()
    
    def on_annotation_selected(self, item):
        """批注列表项被选中"""
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is not None and 0 <= index < len(self.annotations):
            self.current_annotation_index = index
            self.update_navigation()
            self.update_display()


class AnnotationManager:
    """批注管理器（优化版）"""
    
    def __init__(self, text_edit, editor_plugin):
        self.text_edit = text_edit
        self.editor_plugin = editor_plugin
        self.annotations = {}
        self.display_widget = None
        
        # 修改：使用红蓝主题颜色方案
        self.annotation_color = '#ffdcdc'  # 默认浅红色
        self.annotation_colors = [
            '#ffdcdc',  # 浅红色
            '#dcedff',  # 浅蓝色
            '#ffe6e6',  # 稍深的浅红色
            '#e6f2ff',  # 稍深的浅蓝色
            '#fff0f0',  # 更浅的红色
            '#f0f7ff',  # 更浅的蓝色
        ]
        self.current_color_index = 0
        
    def set_annotation_color(self, color):
        """设置批注颜色"""
        # 修复：直接设置颜色属性，不使用不存在的 annotation_manager
        self.annotation_color = color
        
        # 如果有 editor_plugin 引用，更新状态栏
        if self.editor_plugin and hasattr(self.editor_plugin, 'update_status_bar'):
            self.editor_plugin.update_status_bar(f"Annotation color set to {color}")
            
        # 如果有 editor_plugin 引用，设置修改状态
        if self.editor_plugin and hasattr(self.editor_plugin, 'is_modified'):
            self.editor_plugin.is_modified = True
            
    def get_annotation_color(self):
        """获取当前批注颜色"""
        return self.annotation_color
    
    def show_color_menu(self, pos):
        """显示颜色选择菜单"""
        menu = QMenu(self.editor_plugin.widget)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #d1d9e6;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
                color: #1565C0;
            }
        """)
        
        # 添加颜色选项
        color_group = QActionGroup(menu)
        for i, color in enumerate(self.annotation_colors):
            action = QAction(f"Color {i+1}", menu)
            action.setCheckable(True)
            
            # 创建带颜色的图标
            icon_pixmap = QPixmap(16, 16)
            icon_pixmap.fill(QColor(color))
            action.setIcon(QIcon(icon_pixmap))
            
            # 设置当前选中的颜色
            if color == self.annotation_color:
                action.setChecked(True)
            
            # 修复：直接调用 self.set_annotation_color
            action.triggered.connect(lambda checked, c=color: self.set_annotation_color(c))
            menu.addAction(action)
            color_group.addAction(action)
        
        # 添加自定义颜色选项
        menu.addSeparator()
        custom_action = QAction("Custom Color...", menu)
        custom_action.triggered.connect(self.choose_custom_color)
        menu.addAction(custom_action)
        
        menu.exec(pos)
    
    def choose_custom_color(self):
        """选择自定义颜色"""
        color = QColorDialog.getColor(QColor(self.annotation_color), 
                                     self.editor_plugin.widget, 
                                     "Choose Annotation Color")
        if color.isValid():
            self.set_annotation_color(color.name())
    
    def add_annotation(self):
        """为选中文本添加批注（优化版）"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            
            # 创建对话框
            dialog = AnnotationDialog(self.text_edit.parent(), selected_text)
            if dialog.exec():
                annotation_text = dialog.get_annotation_text()
                author = dialog.get_author()
                
                if annotation_text:
                    start = cursor.selectionStart()
                    end = cursor.selectionEnd()
                    
                    # 修改：使用固定的批注颜色，而不是循环使用不同颜色
                    color = self.annotation_color
                    
                    # 创建批注对象
                    annotation = {
                        'text': annotation_text,
                        'author': author,
                        'timestamp': datetime.now().isoformat(),
                        'position': (start, end),
                        'selected_text': selected_text,
                        'color': color,
                        'id': f"{start}_{end}_{datetime.now().timestamp()}"
                    }
                    
                    key = annotation['id']
                    self.annotations[key] = annotation
                    
                    # 应用高亮样式
                    text_format = QTextCharFormat()
                    text_format.setBackground(QColor(color))
                    text_format.setToolTip(
                        f"Author: {author}\n"
                        f"Time: {annotation['timestamp'][:16]}\n"
                        f"Content: {annotation_text}"
                    )
                    cursor.mergeCharFormat(text_format)
                    
                    self.editor_plugin.logger.context(self.editor_plugin.logger.INFO, f"Annotation added: {key}")
                    
                    # 强制刷新文本编辑器的显示
                    self.text_edit.textCursor().clearSelection()
                    self.text_edit.viewport().update()
                    
                    # 显示批注面板
                    self.show_annotations_panel()
                    
                    return True
        else:
            # 如果没有选中文本，显示提示信息
            QMessageBox.information(self.text_edit.parent(), "Info", "Please select text first")
        return False

    def show_annotations_panel(self):
        """显示批注面板 - 修改位置为窗口右侧，并限制高度"""
        if not self.display_widget:
            self.display_widget = AnnotationWidget(self.text_edit)
        
        annotations_list = list(self.annotations.values())
        self.display_widget.set_annotations(annotations_list)
        
        if not self.display_widget.isVisible():
            # 获取主窗口的位置和大小
            main_window = self.text_edit.window()
            if main_window:
                main_window_rect = main_window.frameGeometry()
                
                # 计算批注窗口的位置（主窗口右侧）
                widget_width = self.display_widget.width()
                widget_height = self.display_widget.height()
                
                x = main_window_rect.right() - widget_width - 20  # 离右边距20像素
                y = main_window_rect.top() + 50  # 离顶部50像素
                
                # 确保不会超出屏幕
                screen_geometry = QApplication.primaryScreen().availableGeometry()
                if x + widget_width > screen_geometry.right():
                    x = screen_geometry.right() - widget_width - 20
                
                # 限制批注窗口的高度不超过主窗口的80%，确保在textEdit以内
                max_height = int(main_window_rect.height() * 0.8)
                if widget_height > max_height:
                    self.display_widget.setMaximumHeight(max_height)
                
                # 确保窗口不会超出屏幕底部
                if y + max_height > screen_geometry.bottom():
                    y = screen_geometry.bottom() - max_height - 20
                
                self.display_widget.move(x, y)
            else:
                # 如果无法获取主窗口，使用原来的逻辑
                text_edit_pos = self.text_edit.mapToGlobal(QPoint(0, 0))
                text_edit_rect = self.text_edit.rect()
                
                x = text_edit_pos.x() + text_edit_rect.width() + 10
                y = text_edit_pos.y()
                
                self.display_widget.move(x, y)
            
            self.display_widget.show()
            self.display_widget.raise_()

    def hide_annotations(self):
        """隐藏批注"""
        # 修复：这里应该是 self.display_widget，不是 self.annotation_manager.display_widget
        if self.display_widget:
            self.display_widget.hide()
    
    def toggle_annotations(self):
        """切换批注面板显示状态"""
        # 修复：这里直接检查 self.display_widget
        if not self.display_widget:
            if self.editor_plugin and hasattr(self.editor_plugin, 'logger'):
                self.editor_plugin.logger.context(self.editor_plugin.logger.WARN, "Annotation display widget not initialized")
            return
        
        if self.display_widget.isVisible():
            self.display_widget.hide()
        else:
            self.show_annotations_panel()
    
    def clear_annotations(self):
        """清除所有批注"""
        # 修复：这里直接检查 self.annotations，不是 self.annotation_manager.annotations
        if not self.annotations:
            if self.editor_plugin and hasattr(self.editor_plugin, 'widget'):
                QMessageBox.information(self.editor_plugin.widget, "Info", "No annotations to clear")
            return
        
        if not self.editor_plugin or not hasattr(self.editor_plugin, 'widget'):
            return
            
        reply = QMessageBox.question(
            self.editor_plugin.widget, "Confirm",
            "Clear all annotations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 清除所有高亮
            cursor = self.text_edit.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            
            # 创建默认格式
            default_format = QTextCharFormat()
            default_format.setBackground(QColor("#FFFFFF"))  # 白色背景
            cursor.mergeCharFormat(default_format)
            
            # 清除批注数据
            self.annotations.clear()
            
            # 隐藏批注面板
            if self.display_widget:
                self.display_widget.hide()
            
            # 设置修改状态
            if self.editor_plugin and hasattr(self.editor_plugin, 'is_modified'):
                self.editor_plugin.is_modified = True
                
            # 更新状态栏
            if self.editor_plugin and hasattr(self.editor_plugin, 'update_status_bar'):
                self.editor_plugin.update_status_bar("All annotations cleared")
                
            # 记录日志
            if self.editor_plugin and hasattr(self.editor_plugin, 'logger'):
                self.editor_plugin.logger.context(self.editor_plugin.logger.INFO, "All annotations cleared")

    def get_annotations_list(self):
        """获取批注列表（用于保存）"""
        annotations_list = []
        for ann in self.annotations.values():
            ann_copy = ann.copy()
            if isinstance(ann_copy['position'], tuple):
                ann_copy['position'] = [int(x) for x in ann_copy['position']]
            annotations_list.append(ann_copy)
        return annotations_list
    
    def load_annotations_from_list(self, annotations_list):
        """从列表加载批注"""
        self.annotations.clear()
        
        for ann in annotations_list:
            self.annotations[ann['id']] = ann
            
            # 应用高亮
            cursor = self.text_edit.textCursor()
            start = ann['position'][0]
            end = ann['position'][1]
            
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            
            text_format = QTextCharFormat()
            text_format.setBackground(QColor(ann['color']))
            text_format.setToolTip(
                f"Author: {ann['author']}\n"
                f"Time: {ann['timestamp'][:16]}\n"
                f"Content: {ann['text']}"
            )
            cursor.mergeCharFormat(text_format)
        
        self.editor_plugin.logger.context(
            self.editor_plugin.logger.INFO, 
            f"Annotations loaded: {len(annotations_list)}"
        )
        
        # 清除选择
        self.text_edit.textCursor().clearSelection()
        self.text_edit.viewport().update()


class AnnotationDialog(QDialog):
    """批注对话框 - 美化版"""
    
    def __init__(self, parent=None, selected_text=""):
        super().__init__(parent)
        self.setWindowTitle("Add Annotation")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #333;
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                border: 1.5px solid #d1d9e6;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4a90e2;
                outline: none;
            }
            QPushButton {
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                font-size: 13px;
                border: none;
                min-width: 90px;
            }
            QFrame {
                border-radius: 8px;
            }
        """)
        
        self.setup_ui(selected_text)
    
    def setup_ui(self, selected_text):
        """设置UI - 美化版"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)
        
        # 标题部分
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #5b7cfa;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        
        title_layout = QVBoxLayout()
        title_label = QLabel("📝 Add Annotation")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label)
        title_frame.setLayout(title_layout)
        main_layout.addWidget(title_frame)
        
        # 选中的文本预览卡片
        if selected_text:
            text_card = QFrame()
            text_card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1.5px solid #e1e8f0;
                    border-radius: 8px;
                    padding: 15px;
                }
                QLabel {
                    font-size: 13px;
                }
            """)
            
            text_layout = QVBoxLayout()
            text_label = QLabel("🔍 Selected Text:")
            text_label.setStyleSheet("color: #5b7cfa; font-weight: 600; font-size: 14px;")
            
            # 使用QTextEdit显示选中文本，支持滚动
            text_preview = QTextEdit()
            text_preview.setPlainText(selected_text)
            text_preview.setReadOnly(True)
            text_preview.setMaximumHeight(80)
            text_preview.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #f0f0f0;
                    border-radius: 4px;
                    background-color: #fafbfc;
                    font-style: italic;
                    color: #666;
                    padding: 8px;
                }
            """)
            
            text_layout.addWidget(text_label)
            text_layout.addWidget(text_preview)
            text_card.setLayout(text_layout)
            main_layout.addWidget(text_card)
        
        # 作者输入部分
        author_group = QGroupBox("👤 Author Information")
        author_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                color: #555;
                font-size: 14px;
                border: 1.5px solid #e1e8f0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """)
        
        author_layout = QVBoxLayout()
        author_input_layout = QHBoxLayout()
        author_input_layout.addWidget(QLabel("Author:"))
        self.author_input = QLineEdit("Anonymous")
        self.author_input.setPlaceholderText("Enter your name")
        self.author_input.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #d1d9e6;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #5b7cfa;
            }
        """)
        author_input_layout.addWidget(self.author_input)
        author_layout.addLayout(author_input_layout)
        author_group.setLayout(author_layout)
        main_layout.addWidget(author_group)
        
        # 批注内容部分
        content_group = QGroupBox("📝 Annotation Content")
        content_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                color: #555;
                font-size: 14px;
                border: 1.5px solid #e1e8f0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
        """)
        
        content_layout = QVBoxLayout()
        self.annotation_input = QTextEdit()
        self.annotation_input.setPlaceholderText("Enter annotation content...")
        self.annotation_input.setMinimumHeight(150)
        self.annotation_input.setStyleSheet("""
            QTextEdit {
                border: 1.5px solid #d1d9e6;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #5b7cfa;
            }
        """)
        content_layout.addWidget(self.annotation_input)
        content_group.setLayout(content_layout)
        main_layout.addWidget(content_group)
        
        # 按钮部分
        button_frame = QFrame()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        # 添加弹性空间使按钮居中
        button_layout.addStretch()
        
        ok_button = QPushButton("✅ OK")
        cancel_button = QPushButton("❌ Cancel")
        
        for btn in [ok_button, cancel_button]:
            btn.setFixedHeight(40)
            btn.setMinimumWidth(120)
        
        ok_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5b7cfa, stop:1 #3a5fda);
                color: white;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a8cff, stop:1 #4a6fea);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a6fea, stop:1 #2a4fca);
            }
        """)
        
        cancel_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f7fa, stop:1 #e1e8f0);
                color: #666;
                border: 1.5px solid #d1d9e6;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f0f3fa);
                border-color: #c1c9e6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e1e8f0, stop:1 #d1d9e6);
            }
        """)
        
        button_layout.addWidget(ok_button)
        button_layout.addSpacing(15)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        
        button_frame.setLayout(button_layout)
        main_layout.addWidget(button_frame)
        
        self.setLayout(main_layout)
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
    
    def get_annotation_text(self):
        """获取批注文本"""
        return self.annotation_input.toPlainText()
    
    def get_author(self):
        """获取作者"""
        return self.author_input.text()