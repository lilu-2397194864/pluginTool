"""
思维导图核心类 - 从widgetMind.py中提取的类
"""

import sys
import sqlite3
import os
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsTextItem, QMenu, QMessageBox, QGraphicsPathItem,
    QMenuBar, QFileDialog, QInputDialog, QGraphicsItem  
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QMarginsF, QSettings
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPen, QPainterPath, QAction, 
    QLinearGradient, QCursor, QTextOption, QIcon, QKeySequence
)

# 添加日志支持（如果需要）
from common.ieltsLog import Logger


class MindMapDB:
    """封装所有数据库操作的类"""
    
    def __init__(self, db_path=":memory:"):
        self.logger = Logger("MindMapDB")
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.initialize_db()
        self.pending_changes = False  # 跟踪是否有未提交的更改
    
    def connect(self):
        """连接到数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            QMessageBox.critical(None, "Database Error", f"Cannot connect to database: {str(e)}")
            raise
    
    def initialize_db(self):
        """初始化数据库表结构"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY,
                text TEXT,
                x REAL,
                y REAL,
                width REAL,
                height REAL,
                is_collapsed BOOLEAN DEFAULT 0,
                parent_id INTEGER,
                FOREIGN KEY(parent_id) REFERENCES nodes(id) ON DELETE CASCADE
            )
            """)
            self.pending_changes = True
        except sqlite3.Error as e:
            QMessageBox.critical(None, "Database Error", f"Cannot initialize database: {str(e)}")
            raise
    
    def add_node(self, text, x, y, width, height, is_collapsed, parent_id=None):
        """添加新节点"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO nodes (text, x, y, width, height, is_collapsed, parent_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (text, x, y, width, height, is_collapsed, parent_id))
            node_id = cursor.lastrowid
            self.pending_changes = True
            return node_id
        except sqlite3.Error as e:
            QMessageBox.critical(None, "Database Error", f"Cannot add node: {str(e)}")
            raise
    
    def update_node(self, node_id, **kwargs):
        """更新节点信息"""
        try:
            cursor = self.conn.cursor()
            set_clause = ", ".join(f"{k}=?" for k in kwargs)
            values = list(kwargs.values())
            values.append(node_id)
            cursor.execute(f"""
                UPDATE nodes SET {set_clause} WHERE id=?
            """, values)
            self.pending_changes = True
        except sqlite3.Error as e:
            QMessageBox.critical(None, "Database Error", f"Cannot update node: {str(e)}")
            raise
    
    def delete_node(self, node_id):
        """删除节点及其子节点(级联删除)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM nodes WHERE id=?", (node_id,))
            self.pending_changes = True
        except sqlite3.Error as e:
            QMessageBox.critical(None, "Database Error", f"Cannot delete node: {str(e)}")
            raise
    
    def get_all_nodes(self):
        """获取所有节点数据"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, text, x, y, width, height, is_collapsed, parent_id 
                FROM nodes
            """)
            return cursor.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(None, "Database Error", f"Cannot fetch nodes: {str(e)}")
            raise
    
    def save_to_file(self, file_path):
        """将数据库保存到指定文件（覆盖模式）"""
        try:
            # 先提交当前更改
            if self.pending_changes:
                self.conn.commit()
            
            # 确保文件路径有.db扩展名
            if not file_path.lower().endswith('.db'):
                file_path += '.db'
            
            # 创建新的文件数据库连接
            temp_conn = sqlite3.connect(file_path)
            
            # 使用备份功能复制数据
            self.conn.backup(temp_conn)
            
            # 提交备份
            temp_conn.commit()
            temp_conn.close()
            
            # 关闭旧连接
            self.close()
            
            # 重新连接到新文件
            self.db_path = file_path
            self.connect()
            self.pending_changes = False
            
            return True
            
        except sqlite3.Error as e:
            error_msg = f"Cannot save database to {file_path}: {str(e)}"
            print(error_msg)  # 调试信息
            raise
    
    def commit(self):
        """提交所有挂起的更改"""
        if self.pending_changes:
            self.conn.commit()
            self.pending_changes = False
    
    def close(self):
        """关闭数据库连接"""
        try:
            if self.conn:
                # 先提交未保存的更改
                if self.pending_changes:
                    self.conn.commit()
                self.conn.close()
                self.conn = None
        except Exception as e:
            print(f"Error closing database: {str(e)}")


class ConnectionLine(QGraphicsPathItem):
    def __init__(self, parent_node, child_node):
        super().__init__()
        self.parent_node = parent_node
        self.child_node = child_node
        self.setPen(QPen(QColor(150, 180, 210, 200), 2.0, Qt.PenStyle.SolidLine))
        self.setZValue(-1)
        self.update_path()
        
    def update_path(self):
        parent_center = self.parent_node.scenePos() + QPointF(
            self.parent_node.rect().width(),
            self.parent_node.rect().height() / 2
        )
        child_center = self.child_node.scenePos() + QPointF(
            0,
            self.child_node.rect().height() / 2
        )
        
        distance = abs(child_center.x() - parent_center.x()) * 0.3
        control_point1 = QPointF(parent_center.x() + distance, parent_center.y())
        control_point2 = QPointF(child_center.x() - distance, child_center.y())
        
        path = QPainterPath(parent_center)
        path.cubicTo(control_point1, control_point2, child_center)
        self.setPath(path)


class RoundedRectItem(QGraphicsRectItem):
    def __init__(self, rect, radius=15, parent=None):
        super().__init__(rect, parent)
        self.radius = radius
        self.path = QPainterPath()
        self.update_path()
        
    def update_path(self):
        rect = self.rect()
        self.path = QPainterPath()
        self.path.addRoundedRect(rect, self.radius, self.radius)
        
    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        painter.drawPath(self.path)
        
    def setRect(self, rect):
        super().setRect(rect)
        self.update_path()


class PaddedTextItem(QGraphicsTextItem):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.parent_node = parent
        self.margins = QMarginsF(1, 1, 1, 1)
        
        # 设置焦点相关标志
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)  # 使项可聚焦
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)  # 可选：使项可选中
        
        # 设置文本交互模式
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
 
        doc = self.document()
        doc.setDocumentMargin(0)
        
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.NoWrap)
        option.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        doc.setDefaultTextOption(option)
        
        font = QFont("Times New Roman", 12)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.setFont(font)
        
        self.setDefaultTextColor(QColor(30, 30, 30))
        self.setPlainText(text)
        
        self.document().contentsChanged.connect(self.on_text_changed)
    
    def on_text_changed(self):
        self.parent_node.update_size()
        if self.parent_node.scene():
            self.parent_node.scene().update_node_text_in_db(self.parent_node)
    
    def paint(self, painter, option, widget=None):
        # 保持原有剪裁逻辑
        painter.save()
        clip_rect = QRectF(
            self.margins.left(),
            self.margins.top(),
            self.parent_node.rect().width() - self.margins.left() - self.margins.right(),
            self.parent_node.rect().height() - self.margins.top() - self.margins.bottom()
        )
        painter.setClipRect(clip_rect)
        super().paint(painter, option, widget)
        painter.restore()
 
    # 阻止事件冒泡到父节点
    def mousePressEvent(self, event):
        self.setFocus()
        event.accept()
        super().mousePressEvent(event)
 
    def mouseMoveEvent(self, event):
        event.accept()
        super().mouseMoveEvent(event)
 
    def mouseReleaseEvent(self, event):
        event.accept()
        super().mouseReleaseEvent(event)


class MindMapNode(RoundedRectItem):
    def __init__(self, node_id, text="node", parent=None):
        self.min_width = 100
        self.min_height = 30
        super().__init__(QRectF(0, 0, self.min_width, self.min_height), 2, parent)
        self.node_id = node_id
        self.text = text
        self.child_nodes = []
        self.child_connections = []
        self.parent_connection = None
        self.is_dragging = False
        self.drag_start_pos = QPointF()
        self.is_collapsed = False
        self.child_nodes_visible = True

        self.normal_brush = QBrush(QLinearGradient(0, 0, 0, self.rect().height()))
        self.normal_brush.gradient().setColorAt(0, QColor(224, 248, 240))
        self.normal_brush.gradient().setColorAt(1, QColor(240, 248, 248))
        
        self.selected_brush = QBrush(QLinearGradient(0, 0, 0, self.rect().height()))
        self.selected_brush.gradient().setColorAt(0, QColor(188, 238, 204))
        self.selected_brush.gradient().setColorAt(1, QColor(212, 248, 232))
        
        self.setPen(QPen(QColor(176, 208, 192), 1.5))
        self.setBrush(self.normal_brush)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        self.text_item = PaddedTextItem(text, self)
        self.update_size()
        self.setZValue(1)
    
    def update_size(self):
        doc = self.text_item.document()
        text_width = doc.idealWidth()
        text_height = doc.size().height()
        
        margins = self.text_item.margins
        content_width = text_width + margins.left() + margins.right() + 20
        content_height = text_height + margins.top() + margins.bottom() + 10
        
        new_width = max(self.min_width, content_width)
        new_height = max(self.min_height, content_height)
        
        self.setRect(QRectF(0, 0, new_width, new_height))
        self.text_item.setPos(margins.left(), margins.top())
        
        if self.parent_connection:
            self.parent_connection.update_path()
        for conn in self.child_connections:
            conn.update_path()
        
        if self.scene() and hasattr(self.scene(), 'update_node_dimensions_in_db'):
            self.scene().update_node_dimensions_in_db(self)

    def toggle_children_visibility(self):
        self.is_collapsed = not self.is_collapsed
        self._set_children_visible(not self.is_collapsed)
        self._set_children_connections_visible(not self.is_collapsed)
        
        if self.scene() and hasattr(self.scene(), 'update_node_collapsed_state'):
            self.scene().update_node_collapsed_state(self)
    
    def _set_children_visible(self, visible):
        """递归设置所有子节点可见性（保持自身文本可见）"""
        self.child_nodes_visible = visible
        for child in self.child_nodes:
            child.setVisible(visible and self.isVisible())
            child._set_children_visible(visible)
 
    def _set_children_connections_visible(self, visible):
        """递归设置所有子连接可见性"""
        for conn in self.child_connections:
            conn.setVisible(visible)
        for child in self.child_nodes:
            child._set_children_connections_visible(visible)

    def set_collapsed(self, collapsed):
        """直接设置折叠状态并强制更新子元素可见性"""
        self.is_collapsed = collapsed
        self._set_children_visible(not collapsed)
        self._set_children_connections_visible(not collapsed)
        if self.scene() and hasattr(self.scene(), 'update_node_collapsed_state'):
            self.scene().update_node_collapsed_state(self)

    def add_child(self, child_node):
        """添加子节点时增加可见性判断"""
        self.child_nodes.append(child_node)
        connection = ConnectionLine(self, child_node)
        if self.scene():
            self.scene().addItem(connection)
        self.child_connections.append(connection)
        child_node.parent_connection = connection
 
        # 关键修改：保持当前节点可见性，仅根据折叠状态设置子节点可见性
        child_visible = not self.is_collapsed
        parent_visible = self.isVisible()
        child_node.setVisible(child_visible and parent_visible)
        connection.setVisible(child_visible and parent_visible)

    def remove_child(self, child_node):
        if child_node in self.child_nodes:
            self.child_nodes.remove(child_node)
            for conn in self.child_connections[:]:
                if conn.child_node == child_node:
                    if self.scene():
                        self.scene().removeItem(conn)
                    self.child_connections.remove(conn)
                    child_node.parent_connection = None
                    break

    def contextMenuEvent(self, event):
        menu = QMenu()
        
        toggle_action = QAction("Collapse Children" if not self.is_collapsed else "Expand Children", menu)
        toggle_action.triggered.connect(self.toggle_children_visibility)
        menu.addAction(toggle_action)
        
        add_child_action = QAction("Add Node", menu)
        add_child_action.triggered.connect(lambda: self.scene().add_child_node(self))
        menu.addAction(add_child_action)
        
        delete_action = QAction("Delete Node", menu)
        delete_action.triggered.connect(lambda: self.scene().delete_node(self))
        menu.addAction(delete_action)
        
        menu.exec(event.screenPos())

    def mousePressEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        self.is_dragging = True
        self.drag_start_pos = event.scenePos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.scenePos() - self.drag_start_pos
            self.drag_start_pos = event.scenePos()
            super().mouseMoveEvent(event)
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.is_dragging = False
        
        if self.scene() and hasattr(self.scene(), 'update_node_position_in_db'):
            self.scene().update_node_position_in_db(self)
        
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.parent_connection:
                self.parent_connection.update_path()
            for conn in self.child_connections:
                conn.update_path()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QLinearGradient(0, 0, 0, self.rect().height())))
        self.setZValue(2)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self.setBrush(self.normal_brush if not self.isSelected() else self.selected_brush)
        self.setZValue(1)
        super().hoverLeaveEvent(event)


class MindMapScene(QGraphicsScene):
    def __init__(self, db):
        super().__init__(0, 0, 1920 * 1.5, 1080 * 1.5)
        self.db = db
        self.root_node = None
        self.nodes = {}
        self.load_from_db()
    
    def update_node_position_in_db(self, node):
        """更新节点位置到数据库(不提交)"""
        self.db.update_node(node.node_id, x=node.pos().x(), y=node.pos().y())

    def update_node_text_in_db(self, node):
        """更新节点文本到数据库"""
        self.db.update_node(
            node.node_id,
            text=node.text_item.toPlainText()
        )
 
    def update_node_dimensions_in_db(self, node):
        """更新节点尺寸到数据库"""
        rect = node.rect()
        self.db.update_node(
            node.node_id,
            x=node.pos().x(),
            y=node.pos().y(),
            width=rect.width(),
            height=rect.height()
        )

    def update_node_collapsed_state(self, node):
        """更新节点折叠状态到数据库"""
        self.db.update_node(node.node_id, is_collapsed=node.is_collapsed)

    def load_from_db(self):
        """从数据库加载节点"""
        rows = self.db.get_all_nodes()
        
        if not rows:
            return
        
        # 1. 创建所有节点但不建立父子关系
        nodes = {}
        for row in rows:
            node_id, text, x, y, width, height, is_collapsed, parent_id = row
            node = MindMapNode(node_id, text or "node")
            node.setRect(QRectF(0, 0, width or 100, height or 30))
            node.setPos(x or 0, y or 0)
            node.is_collapsed = bool(is_collapsed)
            nodes[node_id] = node
            self.nodes[node_id] = node
            self.addItem(node)
        
        # 2. 建立父子关系
        for row in rows:
            node_id, _, _, _, _, _, _, parent_id = row
            if parent_id and parent_id in nodes:
                parent = nodes[parent_id]
                child = nodes[node_id]
                parent.add_child(child)
        
        # 3. 设置根节点
        root_ids = [node_id for node_id, data in zip([row[0] for row in rows], rows) 
                   if not data[7] or data[7] == 0]
        if root_ids:
            self.root_node = nodes[root_ids[0]]

    def add_root_node(self, text="Central Topic"):
        """添加根节点"""
        if self.root_node:
            return
        
        scene_width = self.sceneRect().width()
        scene_height = self.sceneRect().height()
        x = scene_width / 2 - 100
        y = scene_height / 2
        
        node_id = self.db.add_node(
            text=text,
            x=x,
            y=y,
            width=100,
            height=30,
            is_collapsed=False,
            parent_id=None
        )
        
        self.root_node = MindMapNode(node_id, text)
        self.root_node.setPos(x, y)
        self.addItem(self.root_node)
        self.nodes[node_id] = self.root_node

    def add_child_node(self, parent_node):
        """添加子节点"""
        child_count = len(parent_node.child_nodes)
        text = f"new node-{child_count + 1}"
        
        golden_angle = math.pi * 2 * 0.618
        radius = 150
        angle = golden_angle * child_count
        
        base_x = parent_node.pos().x() + parent_node.rect().width() + 100
        base_y = parent_node.pos().y()
        
        x_pos = base_x + radius * math.cos(angle)
        y_pos = base_y + radius * math.sin(angle)
        
        node_id = self.db.add_node(
            text=text,
            x=x_pos,
            y=y_pos,
            width=100,
            height=30,
            is_collapsed=False,
            parent_id=parent_node.node_id
        )
        
        child_node = MindMapNode(node_id, text)
        child_node.setPos(x_pos, y_pos)
        self.addItem(child_node)
        parent_node.add_child(child_node)
        self.nodes[node_id] = child_node
    
    def delete_node(self, node):
        """删除节点及其所有子节点"""
        if node == self.root_node:
            QMessageBox.warning(None, "Warning", "Cannot delete root node!")
            return
        
        # 先收集所有要删除的节点ID（包括子节点）
        nodes_to_delete = set()
        def collect_nodes(n):
            nodes_to_delete.add(n.node_id)
            for child in n.child_nodes:
                collect_nodes(child)
        collect_nodes(node)
        
        # 从数据库删除（级联删除由数据库处理）
        self.db.delete_node(node.node_id)
        
        # 从场景中移除所有相关图形项
        def remove_from_scene(n):
            # 移除所有子连接线
            for conn in n.child_connections[:]:
                self.removeItem(conn)
            # 移除父连接线
            if n.parent_connection:
                self.removeItem(n.parent_connection)
            # 移除节点本身
            self.removeItem(n)
            # 从节点字典中移除
            if n.node_id in self.nodes:
                del self.nodes[n.node_id]
        
        # 从场景中移除所有相关节点
        for nid in list(nodes_to_delete):
            if nid in self.nodes:
                remove_from_scene(self.nodes[nid])


class MindMapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger("MindMapWidget")
        self.settings = QSettings("MindMapApp", "MindMapWidget")
        self.current_db_path = self.settings.value("last_db", "mindmap.db")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.shortcuts = {}
        self.styleSheetFile = os.path.join(os.path.dirname(__file__), "widgetMind.css")
        self.active_tab_index = -1
        self.tab_data = []  # 用于存储每个标签页的数据
        
        # 加载样式表
        if os.path.exists(self.styleSheetFile):
            with open(self.styleSheetFile, 'r', encoding='utf-8') as file:
                stylesheet = file.read()
            self.setStyleSheet(stylesheet)
        else:
            # 尝试在当前目录查找
            alt_path = "widgetMind.css"
            if os.path.exists(alt_path):
                with open(alt_path, 'r', encoding='utf-8') as file:
                    stylesheet = file.read()
                self.setStyleSheet(stylesheet)
        
        self.init_ui()
        self.init_menu()
        self.init_context_menu()
        
    def init_ui(self):
        """初始化用户界面"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)  # 显示关闭按钮
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.tab_changed)
        
        self.layout.addWidget(self.tab_widget)
        
        # 添加初始标签页
        self.add_tab(self.current_db_path)
        
    def add_tab(self, db_path, title=None):
        """添加新标签页"""
        try:
            # 创建数据库、场景和视图
            db = MindMapDB(db_path)
            scene = MindMapScene(db)
            view = QGraphicsView()
            view.setRenderHints(QPainter.RenderHint.Antialiasing | 
                             QPainter.RenderHint.SmoothPixmapTransform | 
                             QPainter.RenderHint.TextAntialiasing)
            view.setScene(scene)
            view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            
            # 创建容器部件
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(view)
            
            # 设置标签页标题
            if not title:
                title = os.path.basename(db_path)
                if title.endswith('.db'):
                    title = title[:-3]
                if db_path == ":memory:":
                    title = "Untitled"
            
            # 添加标签页
            tab_index = self.tab_widget.addTab(container, title)
            self.tab_widget.setCurrentIndex(tab_index)
            
            # 存储标签页数据到列表（按添加顺序）
            self.tab_data.append({
                'db': db,
                'db_path': db_path,
                'scene': scene,
                'view': view,
                'container': container
            })
            
            # 如果是新文件，添加根节点
            if not scene.root_node:
                scene.add_root_node("Central Topic")
                
            self.active_tab_index = len(self.tab_data) - 1
            return len(self.tab_data) - 1  # 返回实际插入位置
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
            return -1
    
    def close_tab(self, index):
        """关闭指定标签页（重构索引维护逻辑）"""
        if index < 0 or index >= len(self.tab_data):
            return
 
        # 关闭前保存
        try:
            self.tab_data[index]['db'].commit()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save changes: {str(e)}")
 
        # 关闭数据库
        self.tab_data[index]['db'].close()
 
        # 清理资源
        self.tab_data[index]['scene'].deleteLater()
        self.tab_data[index]['view'].deleteLater()
        self.tab_data[index]['container'].deleteLater()
 
        # 移除标签页和数据
        self.tab_widget.removeTab(index)
        del self.tab_data[index]
 
        # 更新活动标签页索引
        if self.active_tab_index > index:
            self.active_tab_index -= 1
        elif self.active_tab_index == index:
            self.active_tab_index = -1
 
        # 如果关闭了最后一个标签页，添加新的
        if len(self.tab_data) == 0:
            self.add_tab(":memory:", "Untitled")
            self.active_tab_index = 0
        else:
            if self.active_tab_index == -1:
                self.active_tab_index = 0
        self.tab_widget.setCurrentIndex(self.active_tab_index)

    def tab_changed(self, index):
        """标签页切换事件处理（更新索引验证）"""
        if 0 <= index < len(self.tab_data):
            self.active_tab_index = index
            self.current_db_path = self.tab_data[index]['db_path']
            self.settings.setValue("last_db", self.current_db_path)
        else:
            self.active_tab_index = -1
 
    def get_current_tab_data(self):
        """获取当前标签页数据（增加索引验证）"""
        if 0 <= self.active_tab_index < len(self.tab_data):
            return self.tab_data[self.active_tab_index]
        return None
    
    def init_menu(self):
        """初始化菜单栏"""
        self.menu_bar = QMenuBar()
        self.menu_bar.setVisible(False)
        
        # 文件菜单
        file_menu = self.menu_bar.addMenu("&File")

        # 新建文件
        new_action = QAction(QIcon.fromTheme("document-new"), "&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setStatusTip("Create new mind map")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        # 打开文件
        open_action = QAction(QIcon.fromTheme("document-open"), "&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setStatusTip("Open existing mind map")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # 保存文件
        save_action = QAction(QIcon.fromTheme("document-save"), "&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setStatusTip("Save current mind map")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        # 另存为
        save_as_action = QAction(QIcon.fromTheme("document-save-as"), "Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.setStatusTip("Save current mind map with new name")
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        # 关闭标签页
        close_tab_action = QAction("Close &Tab", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.setStatusTip("Close current tab")
        close_tab_action.triggered.connect(self.close_current_tab)
        file_menu.addAction(close_tab_action)
        
        # 最近文件
        self.recent_menu = file_menu.addMenu("&Recent")
        self.update_recent_files()
        
        file_menu.addSeparator()
        
        # 切换菜单
        self.toggle_menu_action = QAction("Show/Hide &Menu", self)
        self.toggle_menu_action.setShortcut(QKeySequence("Ctrl+M"))
        self.toggle_menu_action.setStatusTip("Toggle menu bar visibility")
        self.toggle_menu_action.triggered.connect(self.toggle_menu)
        file_menu.addAction(self.toggle_menu_action)
        
        # 帮助菜单
        help_menu = self.menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.setShortcut(QKeySequence("Ctrl+A"))
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        self.layout.setMenuBar(self.menu_bar)
        self.setup_shortcuts()
    
    def close_current_tab(self):
        """关闭当前标签页"""
        if self.active_tab_index >= 0:
            self.close_tab(self.active_tab_index)
    
    def init_context_menu(self):
        """初始化上下文菜单"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.show_menu_action = QAction("Show Menu Bar", self)
        self.show_menu_action.setShortcut(QKeySequence("Ctrl+M"))
        self.show_menu_action.triggered.connect(self.show_menu)
        self.show_menu_action.setVisible(True)
        self.addAction(self.show_menu_action)
        
        sep = QAction(self)
        sep.setSeparator(True)
        self.addAction(sep)

    def setup_shortcuts(self):
        """设置快捷键"""
        shortcuts = [
            ("New file", QKeySequence.StandardKey.New, self.new_file),
            ("Open file", QKeySequence.StandardKey.Open, self.open_file),
            ("Save file", QKeySequence.StandardKey.Save, self.save_file),
            ("Save as file", QKeySequence.StandardKey.SaveAs, self.save_as_file),
            ("Close tab", QKeySequence("Ctrl+W"), self.close_current_tab),
            ("Update recent", QKeySequence("Ctrl+R"), self.update_recent_files),
            ("About", QKeySequence("Ctrl+A"), self.show_about)
        ]
        
        for name, shortcut, callback in shortcuts:
            action = QAction(name, self)
            action.triggered.connect(callback)
            self.addAction(action)
            self.shortcuts[name] = action

    def toggle_menu(self):
        """切换菜单栏可见性"""
        visible = not self.menu_bar.isVisible()
        self.menu_bar.setVisible(visible)
        self.show_menu_action.setVisible(not visible)
        title = "Mind Map Application" if visible else "Mind Map Application (Menu Hidden - Press Esc or Ctrl+M)"
        self.window().setWindowTitle(title)

    def show_menu(self):
        """显示菜单栏"""
        self.menu_bar.setVisible(True)
        self.show_menu_action.setVisible(False)
        self.window().setWindowTitle("Mind Map Application")

    def update_recent_files(self):
        """更新最近文件菜单"""
        self.recent_menu.clear()
        recent_files = self.settings.value("recent_files", [])
        
        if not recent_files:
            action = QAction("No recent files", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return
        
        for i, file_path in enumerate(recent_files[:5]):
            if os.path.exists(file_path):
                action = QAction(f"{i+1}. {os.path.basename(file_path)}", self)
                action.setData(file_path)
                action.triggered.connect(lambda checked, path=file_path: self.load_file(path))
                self.recent_menu.addAction(action)
        
        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self.clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def clear_recent_files(self):
        """清除最近文件列表"""
        self.settings.setValue("recent_files", [])
        self.update_recent_files()

    def new_file(self):
        """创建新文件"""
        file_name, ok = QInputDialog.getText(
            self, "New Mind Map", "Enter file name (without extension):"
        )
        
        if ok and file_name:
            file_path = f"{file_name}.db"
            if os.path.exists(file_path):
                QMessageBox.warning(self, "Warning", f"File {file_path} already exists!")
                return
            
            try:
                self.add_tab(file_path)
                self.add_to_recent_files(file_path)
                QMessageBox.information(self, "Success", f"Created new mind map: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create file: {str(e)}")

    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Mind Map", "", "Database Files (*.db);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        """加载文件"""
        # 检查文件是否已经打开
        for index in range(len(self.tab_data)):
            tab_data = self.tab_data[index]
            if tab_data['db_path'] == file_path:
                self.tab_widget.setCurrentIndex(index)
                return
                
        # 在新标签页中打开
        index = self.add_tab(file_path)
        if index >= 0:
            self.add_to_recent_files(file_path)

    def save_file(self):
        """保存当前文件"""
        tab_data = self.get_current_tab_data()
        if not tab_data:
            QMessageBox.warning(self, "Warning", "No active tab to save.")
            return
            
        if tab_data['db_path'] == ":memory:":
            self.save_as_file()
            return
        
        try:
            
            # 提交更改
            tab_data['db'].commit()
            # 显示保存成功消息（可选）
            if self.settings.value("show_save_confirmation", "true").lower() == "true":
                QMessageBox.information(
                    self, 
                    "Saved", 
                    f"Mind map saved to:\n{tab_data['db_path']}"
                )
            self.logger.context(self.logger.INFO, f"Saved to {tab_data['db_path']}")
            
        except Exception as e:
            error_msg = f"Failed to save: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def save_as_file(self):
        """另存为文件（保持当前标签页不变）"""
        tab_data = self.get_current_tab_data()
        if not tab_data:
            QMessageBox.warning(self, "Warning", "No active tab to save.")
            return
        
        try:
            # 先提交当前更改
            tab_data['db'].commit()
            
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Mind Map As", 
                os.path.dirname(tab_data['db_path']) if tab_data['db_path'] != ":memory:" else "",
                "Database Files (*.db);;All Files (*)"
            )
            
            if not file_path:
                return  # 用户取消操作
            
            # 确保文件扩展名
            if not file_path.lower().endswith('.db'):
                file_path += '.db'
            
            # 检查文件是否已存在
            if os.path.exists(file_path):
                reply = QMessageBox.question(
                    self, 
                    "File Exists", 
                    f"File '{os.path.basename(file_path)}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            try:
                # 保存到新文件
                success = tab_data['db'].save_to_file(file_path)
                
                if success:
                    # 更新当前标签页的数据
                    old_db_path = tab_data['db_path']
                    tab_data['db_path'] = file_path
                    
                    # 更新标签页标题
                    tab_index = self.tab_widget.indexOf(tab_data['container'])
                    if tab_index >= 0:
                        title = os.path.basename(file_path)
                        if title.endswith('.db'):
                            title = title[:-3]
                        self.tab_widget.setTabText(tab_index, title)
                    
                    # 更新当前数据库路径
                    self.current_db_path = file_path
                    self.settings.setValue("last_db", file_path)
                    
                    # 添加到最近文件列表
                    self.add_to_recent_files(file_path)
                    
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"Mind map saved as:\n{file_path}"
                    )
                    
                    self.logger.context(self.logger.INFO, f"Saved as {file_path}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to save mind map.")
                    
            except Exception as save_error:
                raise save_error
                
        except Exception as e:
            error_msg = f"Save failed: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def add_to_recent_files(self, file_path):
        """添加到最近文件列表"""
        recent_files = self.settings.value("recent_files", [])
        
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        recent_files.insert(0, file_path)
        self.settings.setValue("recent_files", recent_files[:5])
        self.update_recent_files()

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "About Mind Map", 
                         "Mind Map Application\nVersion 1.0\n\nA simple mind mapping tool.")

    def closeEvent(self, event):
        """关闭事件处理"""
        # 关闭前保存所有打开的文件
        for index in range(len(self.tab_data)):
            tab_data = self.tab_data[index]
            try:
                tab_data['db'].commit()
                tab_data['db'].close()
            except:
                pass
        
        self.settings.setValue("last_db", self.current_db_path)
        super().closeEvent(event)