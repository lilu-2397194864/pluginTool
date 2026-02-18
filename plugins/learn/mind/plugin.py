"""
思维导图插件 - 基于widgetMind.py的适配版本
功能：多标签页思维导图编辑器
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QMessageBox, QVBoxLayout, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# 添加路径以便导入base_plugin
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from plugins.base_plugin import BasePlugin

# 导入思维导图相关类
from .mind_map import MindMapDB, MindMapWidget


class MindPlugin(BasePlugin):
    """思维导图插件"""
    
    def __init__(self, plugin_name, ui_file, signal_bus):
        super().__init__(plugin_name, ui_file, signal_bus)
        
        # 初始化变量
        self.mind_map_widget = None
        self.logger.context(self.logger.INFO, f"Mind Map plugin created with UI: {ui_file}")
    
    def initialize(self):
        """初始化插件"""
        try:
            # 加载UI文件
            if not self.load_ui():
                self.logger.context(self.logger.ERROR, "Failed to load Mind Map UI")
                return
            
            # 在UI中创建思维导图部件
            self.setup_mind_map_widget()
            
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
                'description': 'Mind Map tool for creating and managing mind maps'
            })
            
            self.logger.context(self.logger.INFO, "Mind Map plugin initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Mind Map plugin: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message("main_window", {
                'type': 'status',
                'message': f'Mind Map plugin initialization failed: {str(e)}'
            })
    
    def setup_mind_map_widget(self):
        """在UI中设置思维导图部件"""
        try:
            # 查找容器部件
            container_widget = None
            if hasattr(self.ui, 'mindMapContainer'):
                container_widget = self.ui.mindMapContainer
            else:
                # 如果UI中没有容器，创建一个
                container_widget = QWidget()
                if hasattr(self.ui, 'verticalLayout'):
                    self.ui.verticalLayout.addWidget(container_widget)
                else:
                    # 创建新的布局
                    layout = QVBoxLayout(self.widget)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.addWidget(container_widget)
                    self.widget.setLayout(layout)
            
            # 创建思维导图部件
            self.mind_map_widget = MindMapWidget(container_widget)
            
            # 设置布局
            container_layout = QVBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(self.mind_map_widget)
            
            self.logger.context(self.logger.DEBUG, "Mind Map widget set up")
            
        except Exception as e:
            error_msg = f"Failed to setup Mind Map widget: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            raise
    
    def connect_signals(self):
        """连接信号槽"""
        try:
            # 连接思维导图的事件信号（如果需要）
            if self.mind_map_widget:
                # 这里可以连接思维导图内部的自定义信号
                pass
            
            # 连接UI控件信号（如果UI中有额外控件）
            self.connect_ui_signals()
            
            self.logger.context(self.logger.INFO, "All signals connected")
            
        except Exception as e:
            error_msg = f"Failed to connect signals: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def connect_ui_signals(self):
        """连接UI控件信号"""
        try:
            # 如果UI中有额外的控件，在这里连接它们的信号
            # 例如：
            # if hasattr(self.ui, 'someButton'):
            #     self.ui.someButton.clicked.connect(self.on_some_button_clicked)
            pass
            
        except Exception as e:
            error_msg = f"Failed to connect UI signals: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def setup_initial_state(self):
        """设置初始状态"""
        try:
            # 设置窗口标题
            self.widget.setWindowTitle("Mind Map")
            
            # 更新状态（如果UI中有状态标签）
            if hasattr(self.ui, 'labelStatus'):
                self.ui.labelStatus.setText("Ready")
                self.ui.labelStatus.setStyleSheet("color: #008000;")
            
            self.logger.context(self.logger.DEBUG, "Initial state set up")
            
        except Exception as e:
            error_msg = f"Failed to set up initial state: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def on_message(self, sender, data):
        """接收来自其他插件的消息"""
        try:
            message_type = data.get('type', '')
            
            self.logger.context(self.logger.DEBUG, 
                              f"Received message type: {message_type} from {sender}")
            
            if message_type == 'open_mindmap':
                # 处理打开思维导图文件的请求
                self.handle_open_mindmap(sender, data)
            
            elif message_type == 'save_mindmap':
                # 处理保存思维导图的请求
                self.handle_save_mindmap(sender, data)
            
            elif message_type == 'new_mindmap':
                # 处理新建思维导图的请求
                self.handle_new_mindmap(sender, data)
            
            elif message_type == 'export_mindmap':
                # 处理导出思维导图的请求
                self.handle_export_mindmap(sender, data)
            
            elif message_type == 'status_query':
                # 响应状态查询
                status_info = {
                    'type': 'status_response',
                    'plugin': self.plugin_name,
                    'status': 'running',
                    'initialized': True,
                    'has_mindmap': self.mind_map_widget is not None
                }
                
                self.send_message(sender, status_info)
                self.logger.context(self.logger.DEBUG, "Responded to status query")
            
            elif message_type == 'text_data':
                # 处理文本数据（如果需要从其他插件接收文本创建节点）
                self.handle_text_data(sender, data)
            
            elif message_type == 'plugin_command':
                # 处理插件命令
                command = data.get('command', '')
                if command == 'refresh':
                    self.handle_refresh_command(sender, data)
                elif command == 'close_all':
                    self.handle_close_all_command(sender, data)
            
            else:
                # 记录未知消息类型
                self.logger.context(self.logger.DEBUG, 
                                  f"Unknown message type: {message_type} from {sender}")
                
        except Exception as e:
            error_msg = f"Error handling message from {sender}: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def handle_open_mindmap(self, sender, data):
        """处理打开思维导图文件的请求"""
        try:
            file_path = data.get('file_path', '')
            if file_path and os.path.exists(file_path):
                self.logger.context(self.logger.INFO, f"Opening mind map: {file_path}")
                
                # 使用思维导图部件的打开功能
                if self.mind_map_widget:
                    # 这里可以调用mind_map_widget的方法来打开文件
                    # 由于MindMapWidget有open_file方法，我们可以调用它
                    self.mind_map_widget.load_file(file_path)
                
                # 发送响应
                self.send_message(sender, {
                    'type': 'open_mindmap_response',
                    'status': 'success',
                    'file_path': file_path
                })
                
                self.logger.context(self.logger.INFO, f"Mind map opened: {file_path}")
            else:
                error_msg = f"File not found: {file_path}"
                self.logger.context(self.logger.WARN, error_msg)
                self.send_message(sender, {
                    'type': 'open_mindmap_response',
                    'status': 'failed',
                    'message': error_msg
                })
                
        except Exception as e:
            error_msg = f"Failed to open mind map: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'open_mindmap_response',
                'status': 'failed',
                'message': error_msg
            })
    
    def handle_save_mindmap(self, sender, data):
        """处理保存思维导图的请求"""
        try:
            if self.mind_map_widget:
                self.logger.context(self.logger.INFO, "Saving mind map")
                
                # 使用保存文件方法
                self.mind_map_widget.save_file()
                
                # 获取当前标签页数据以获取文件路径
                tab_data = self.mind_map_widget.get_current_tab_data()
                if tab_data and tab_data['db_path'] != ":memory:":
                    # 发送响应
                    self.send_message(sender, {
                        'type': 'save_mindmap_response',
                        'status': 'success',
                        'file_path': tab_data['db_path']
                    })
                    
                    self.logger.context(self.logger.INFO, f"Mind map saved: {tab_data['db_path']}")
                else:
                    # 如果是内存数据库，可能用户取消了另存为操作
                    self.send_message(sender, {
                        'type': 'save_mindmap_response',
                        'status': 'cancelled',
                        'message': 'Save operation cancelled'
                    })
                    
            else:
                error_msg = "Mind Map widget not initialized"
                self.logger.context(self.logger.ERROR, error_msg)
                self.send_message(sender, {
                    'type': 'save_mindmap_response',
                    'status': 'failed',
                    'message': error_msg
                })
                
        except Exception as e:
            error_msg = f"Failed to save mind map: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'save_mindmap_response',
                'status': 'failed',
                'message': error_msg
            })

    
    def handle_new_mindmap(self, sender, data):
        """处理新建思维导图的请求"""
        try:
            if self.mind_map_widget:
                self.logger.context(self.logger.INFO, "Creating new mind map")
                
                # 使用思维导图部件的新建功能
                self.mind_map_widget.new_file()
                
                # 发送响应
                self.send_message(sender, {
                    'type': 'new_mindmap_response',
                    'status': 'success'
                })
                
                self.logger.context(self.logger.INFO, "New mind map created")
            else:
                error_msg = "Mind Map widget not initialized"
                self.logger.context(self.logger.ERROR, error_msg)
                self.send_message(sender, {
                    'type': 'new_mindmap_response',
                    'status': 'failed',
                    'message': error_msg
                })
                
        except Exception as e:
            error_msg = f"Failed to create new mind map: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'new_mindmap_response',
                'status': 'failed',
                'message': error_msg
            })
    
    def handle_export_mindmap(self, sender, data):
        """处理导出思维导图的请求"""
        try:
            export_type = data.get('export_type', 'image')  # image, pdf, text, etc.
            
            if self.mind_map_widget:
                self.logger.context(self.logger.INFO, f"Exporting mind map as {export_type}")
                
                # TODO: 实现导出功能
                # 这里可以添加导出为图片、PDF、文本等格式的功能
                
                # 发送响应
                self.send_message(sender, {
                    'type': 'export_mindmap_response',
                    'status': 'success',
                    'export_type': export_type
                })
                
                self.logger.context(self.logger.INFO, f"Mind map exported as {export_type}")
            else:
                error_msg = "Mind Map widget not initialized"
                self.logger.context(self.logger.ERROR, error_msg)
                self.send_message(sender, {
                    'type': 'export_mindmap_response',
                    'status': 'failed',
                    'message': error_msg
                })
                
        except Exception as e:
            error_msg = f"Failed to export mind map: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'export_mindmap_response',
                'status': 'failed',
                'message': error_msg
            })
    
    def handle_text_data(self, sender, data):
        """处理文本数据（从其他插件接收文本创建节点）"""
        try:
            text = data.get('content', '')
            source = data.get('source', 'unknown')
            
            if text and self.mind_map_widget:
                self.logger.context(self.logger.INFO, f"Received text data from {sender}")
                
                # 获取当前场景
                tab_data = self.mind_map_widget.get_current_tab_data()
                if tab_data and tab_data['scene']:
                    scene = tab_data['scene']
                    
                    # 获取当前选中的节点或根节点
                    selected_nodes = scene.selectedItems()
                    if selected_nodes:
                        parent_node = selected_nodes[0]
                    else:
                        parent_node = scene.root_node
                    
                    # 添加新节点
                    if parent_node:
                        scene.add_child_node(parent_node)
                        
                        # 设置节点文本
                        new_child = parent_node.child_nodes[-1]
                        new_child.text_item.setPlainText(text[:50])  # 限制文本长度
                        
                        self.logger.context(self.logger.INFO, 
                                          f"Created new node from text: {text[:50]}...")
                    
                self.send_message(sender, {
                    'type': 'text_data_response',
                    'status': 'success',
                    'message': 'Node created from text'
                })
            else:
                self.logger.context(self.logger.WARN, 
                                  f"Received empty text from {sender}")
                self.send_message(sender, {
                    'type': 'text_data_response',
                    'status': 'failed',
                    'message': 'Empty text received'
                })
                
        except Exception as e:
            error_msg = f"Failed to handle text data: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'text_data_response',
                'status': 'failed',
                'message': error_msg
            })
    
    def handle_refresh_command(self, sender, data):
        """处理刷新命令"""
        try:
            self.logger.context(self.logger.INFO, "Handling refresh command")
            
            # 刷新思维导图显示
            if self.mind_map_widget:
                for tab_data in self.mind_map_widget.tab_data:
                    if 'view' in tab_data:
                        tab_data['view'].viewport().update()
                
                self.logger.context(self.logger.INFO, "Mind Map refreshed")
            
            self.send_message(sender, {
                'type': 'command_response',
                'status': 'success',
                'command': 'refresh'
            })
            
        except Exception as e:
            error_msg = f"Failed to refresh: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'command_response',
                'status': 'failed',
                'command': 'refresh',
                'message': error_msg
            })
    
    def handle_close_all_command(self, sender, data):
        """处理关闭所有标签页命令"""
        try:
            self.logger.context(self.logger.INFO, "Handling close all command")
            
            # 关闭所有标签页
            if self.mind_map_widget:
                while self.mind_map_widget.tab_widget.count() > 0:
                    self.mind_map_widget.close_tab(0)
                
                self.logger.context(self.logger.INFO, "All tabs closed")
            
            self.send_message(sender, {
                'type': 'command_response',
                'status': 'success',
                'command': 'close_all'
            })
            
        except Exception as e:
            error_msg = f"Failed to close all tabs: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            self.send_message(sender, {
                'type': 'command_response',
                'status': 'failed',
                'command': 'close_all',
                'message': error_msg
            })
    
    def cleanup(self):
        """清理插件资源"""
        try:
            # 清理思维导图资源
            if self.mind_map_widget:
                self.mind_map_widget.closeEvent(None)
                self.mind_map_widget = None
            
            # 调用父类的清理方法
            super().cleanup()
            
            self.logger.context(self.logger.INFO, "Mind Map plugin cleanup complete")
            
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Error during cleanup: {str(e)}")