from abc import ABC, abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi
import os
import sys

# Add parent directory to path for ieltsLog import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.ieltsLog import Logger


class PluginSignal(QObject):
    """Global communication signal bus"""
    
    # Define global signals
    plugin_message = pyqtSignal(str, str, dict)  # sender, receiver, data
    
    def send_message(self, sender, receiver, data):
        """Send a message"""
        self.plugin_message.emit(sender, receiver, data)


class BasePlugin(ABC):
    """Base plugin class, all plugins must inherit from this class"""
    
    def __init__(self, plugin_name, ui_file, signal_bus):
        """Initialize plugin"""
        self.plugin_name = plugin_name
        self.ui_file = ui_file
        self.signal_bus = signal_bus
        self.widget = None
        self.ui = None
        self.logger = Logger(f"Plugin.{plugin_name}")
        
        # Connect to global signal
        if signal_bus:
            self.signal_bus.plugin_message.connect(self._handle_message)
    
    @abstractmethod
    def initialize(self):
        """Initialize plugin (must be implemented by subclass)"""
        pass
    
    @abstractmethod
    def on_message(self, sender, data):
        """Receive message (must be implemented by subclass)"""
        pass
    
    def _handle_message(self, sender, receiver, data):
        """Internal handler for incoming messages"""
        try:
            # Check if message is for this plugin
            if receiver == self.plugin_name or receiver == "all":
                self.logger.context(self.logger.DEBUG, 
                                   f"Received message from {sender}: {data.get('type', 'unknown')}")
                self.on_message(sender, data)
        except Exception as e:
            self.logger.context(self.logger.ERROR, 
                               f"Error handling message from {sender}: {str(e)}")
    
    def load_ui(self):
        """Load UI file"""
        try:
            # Check if UI file exists
            if not os.path.exists(self.ui_file):
                # Try to find in plugin directory
                alt_path = os.path.join("plugins", self.ui_file)
                if os.path.exists(alt_path):
                    self.ui_file = alt_path
                else:
                    raise FileNotFoundError(f"UI file not found: {self.ui_file}")
            
            # Load UI file
            self.widget = QWidget()
            self.ui = loadUi(self.ui_file, self.widget)
            
            # Set object name for debugging
            self.widget.setObjectName(f"widget_{self.plugin_name}")
            
            self.logger.context(self.logger.INFO, f"UI loaded successfully: {self.ui_file}")
            return True
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to load UI {self.ui_file}: {str(e)}")
            # Create fallback interface
            self.create_fallback_ui()
            return False
    
    def create_fallback_ui(self):
        """Create fallback interface (when UI file loading fails)"""
        self.widget = QWidget()
        self.widget.setObjectName(f"widget_{self.plugin_name}_fallback")
        
        # Add basic interface elements
        layout = QVBoxLayout(self.widget)
        label = QLabel(f"Plugin: {self.plugin_name}\nUI file loading failed: {self.ui_file}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        self.ui = self.widget  # Simplified handling
        self.logger.context(self.logger.WARN, f"Created fallback UI for {self.plugin_name}")
    
    def get_widget(self):
        """Get plugin interface widget"""
        return self.widget
    
    def send_message(self, receiver, data):
        """Send a message"""
        try:
            self.logger.context(self.logger.DEBUG, 
                               f"Sending message to {receiver}: {data.get('type', 'unknown')}")
            self.signal_bus.send_message(self.plugin_name, receiver, data)
        except Exception as e:
            self.logger.context(self.logger.ERROR, 
                               f"Failed to send message to {receiver}: {str(e)}")
    
    def broadcast_message(self, data):
        """Broadcast message to all plugins"""
        self.send_message("all", data)
    
    def cleanup(self):
        """Clean up plugin resources (can be overridden by subclass)"""
        try:
            # Disconnect from signal bus
            if self.signal_bus:
                self.signal_bus.plugin_message.disconnect(self._handle_message)
            self.logger.context(self.logger.INFO, f"Plugin {self.plugin_name} cleaned up")
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor"""
        self.cleanup()