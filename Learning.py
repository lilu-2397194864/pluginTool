import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QMessageBox
)

# Add parent directory to path for ieltsLog import 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.plugin_manager import PluginManager
from plugins.base_plugin import PluginSignal
from common.ieltsLog import Logger


class MainWindow(QMainWindow):
    """Main window class, responsible for managing plugin framework"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger("MainWindow")
        self.setWindowTitle("My Tools")
        self.resize(1400, 900)
        
        # Store plugin instances
        self.plugin_instances = {}
        
        # Initialize central widget
        self.init_ui()
        
        # Plugin manager
        self.plugin_manager = PluginManager()
        
        # Global signal bus
        self.global_signal = PluginSignal()
        
        # Connect global signals
        self.global_signal.plugin_message.connect(self.handle_global_message)
        
        # Load configuration
        self.load_config()
        
        self.logger.context(self.logger.INFO, "Main window initialized")
    
    def init_ui(self):
        """Initialize user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        
        # Primary tab widget (plugin categories)
        self.main_tab_widget = QTabWidget()
        self.main_tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.main_tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.main_tab_widget)
    
    def load_config(self):
        """Load plugin configuration from config file"""
        try:
            config_file = "config.json"
            if not os.path.exists(config_file):
                QMessageBox.critical(self, "Error", f"Config file not found: {config_file}")
                self.logger.context(self.logger.ERROR, f"Config file not found: {config_file}")
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Clear existing plugins
            self.clear_all_plugins()
            
            # Load plugin categories as per configuration
            for category_config in config['categories']:
                category_name = category_config['name']
                plugins = category_config['plugins']
                
                # Create category page
                category_widget = self.create_category_page(category_name)
                self.main_tab_widget.addTab(category_widget, category_name)
                
                # Load all plugins under this category
                for plugin_config in plugins:
                    # Only load enabled plugins
                    if plugin_config.get('enabled', True):
                        self.load_plugin(category_name, plugin_config)
            
            self.logger.context(self.logger.INFO, f"Configuration loaded from {config_file}")
                    
        except Exception as e:
            error_msg = f"Failed to load config file: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
            QMessageBox.critical(self, "Configuration Error", error_msg)
    
    def create_category_page(self, category_name):
        """Create plugin category page"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Secondary tab widget (specific plugins)
        sub_tab_widget = QTabWidget()
        sub_tab_widget.setTabPosition(QTabWidget.TabPosition.South)
        sub_tab_widget.setDocumentMode(True)
        sub_tab_widget.setObjectName(f"tab_{category_name}")
        layout.addWidget(sub_tab_widget)
        
        return widget
    
    def load_plugin(self, category_name, plugin_config):
        """Load a single plugin"""
        try:
            plugin_name = plugin_config['name']
            ui_file = plugin_config['ui_file']
            
            self.logger.context(self.logger.INFO, f"Loading plugin: {category_name}.{plugin_name}")
            
            # Get secondary tab widget of category page
            try:
                category_index = [self.main_tab_widget.tabText(i) 
                                for i in range(self.main_tab_widget.count())].index(category_name)
                category_widget = self.main_tab_widget.widget(category_index)
                sub_tab_widget = category_widget.findChild(QTabWidget)
            except Exception as e:
                self.logger.context(self.logger.ERROR, f"Failed to find tab widget for {category_name}: {str(e)}")
                return
            
            # Load plugin through plugin manager
            plugin_instance = self.plugin_manager.load_plugin(
                category_name, 
                plugin_name,
                ui_file,
                self.global_signal
            )
            
            if plugin_instance and plugin_instance.widget:
                # Add to secondary tab
                sub_tab_widget.addTab(plugin_instance.widget, plugin_name)
                
                # Store plugin instance
                key = f"{category_name}.{plugin_name}"
                self.plugin_instances[key] = plugin_instance
                
                self.logger.context(self.logger.INFO, f"Plugin loaded successfully: {category_name}.{plugin_name}")
            else:
                error_msg = f"Plugin loading failed: {category_name}.{plugin_name}"
                self.logger.context(self.logger.ERROR, error_msg)
                
        except Exception as e:
            error_msg = f"Failed to load plugin {category_name}.{plugin_config['name']}: {str(e)}"
            self.logger.context(self.logger.ERROR, error_msg)
    
    def clear_all_plugins(self):
        """Clear all plugins"""
        # Unload plugin instances
        for instance in self.plugin_instances.values():
            if hasattr(instance, 'cleanup'):
                instance.cleanup()
        self.plugin_instances.clear()
        
        # Clear tab widgets
        self.main_tab_widget.clear()
        
        self.logger.context(self.logger.INFO, "All plugins cleared")
    
    def refresh_plugins(self):
        """Refresh plugins (reload configuration)"""
        reply = QMessageBox.question(
            self, "Refresh Plugins", 
            "Are you sure you want to reload all plugins? Unsaved data may be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.load_config()
            QMessageBox.information(self, "Refresh Complete", "Plugins have been reloaded.")
            self.logger.context(self.logger.INFO, "Plugins refreshed")
    
    def show_about(self):
        """Show about information"""
        QMessageBox.about(
            self, "About Dynamic Plugin System",
            "Dynamic Plugin System v2.0\n\n"
            "This is an application framework supporting dynamic plugin loading.\n"
            "Plugins are managed by category and support inter-plugin communication.\n\n"
            "Features:\n"
            "• Support dynamic loading/unloading of plugins\n"
            "• Two-level category management\n"
            "• Inter-plugin communication mechanism\n"
            "• Configuration file management\n"
        )
    
    def handle_global_message(self, sender, receiver, data):
        """Handle global messages"""
        # Add global message handling logic here
        if receiver == "main_window":
            if data.get('type') == 'status':
                message = data.get('message', '')
                self.statusBar().showMessage(message, 3000)
                self.logger.context(self.logger.DEBUG, f"Status message from {sender}: {message}")
        
        # Log all messages for debugging
        self.logger.context(self.logger.DEBUG, 
                           f"Global message: sender={sender}, receiver={receiver}, type={data.get('type', 'unknown')}")
    
    def closeEvent(self, event):
        """Window close event"""
        # Clean up plugin resources
        self.logger.context(self.logger.INFO, "Application closing, cleaning up plugins")
        self.plugin_manager.unload_all()
        event.accept()


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()