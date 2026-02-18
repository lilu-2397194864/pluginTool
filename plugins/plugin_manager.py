import importlib
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox

# Add parent directory to path for ieltsLog import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.ieltsLog import Logger


class PluginManager:
    """Plugin manager, responsible for dynamic loading and unloading of plugins"""
    
    def __init__(self):
        self.plugin_instances = {}
        self.loaded_modules = {}
        self.logger = Logger("PluginManager")
    
    def load_plugin(self, category, plugin_name, ui_file, signal_bus):
        """Dynamically load a plugin
        
        Args:
            category: Plugin category
            plugin_name: Plugin name
            ui_file: UI file path
            signal_bus: Signal bus instance
            
        Returns:
            Plugin instance or None
        """
        try:
            # Build plugin module path
            module_path = f"plugins.{category}.{plugin_name}.plugin"
            
            self.logger.context(self.logger.INFO, f"Loading plugin: {module_path}")
            
            # Dynamically import plugin module
            if module_path in self.loaded_modules:
                module = self.loaded_modules[module_path]
                # Reload module to support hot updates
                module = importlib.reload(module)
                self.logger.context(self.logger.DEBUG, f"Reloaded module: {module_path}")
            else:
                module = importlib.import_module(module_path)
                self.loaded_modules[module_path] = module
                self.logger.context(self.logger.DEBUG, f"Imported module: {module_path}")
            
            # Get plugin class (naming convention: capitalized plugin name + Plugin)
            plugin_class_name = f"{plugin_name.capitalize()}Plugin"
            
            if hasattr(module, plugin_class_name):
                plugin_class = getattr(module, plugin_class_name)
                self.logger.context(self.logger.DEBUG, f"Found plugin class: {plugin_class_name}")
            else:
                # Try to find other possible class names
                for attr_name in dir(module):
                    if attr_name.endswith('Plugin'):
                        plugin_class = getattr(module, attr_name)
                        self.logger.context(self.logger.DEBUG, f"Found plugin class: {attr_name}")
                        break
                else:
                    raise AttributeError(f"Plugin class not found in module: {plugin_class_name}")
            
            # Resolve UI file path
            resolved_ui_file = self.resolve_ui_file_path(category, plugin_name, ui_file)
            self.logger.context(self.logger.DEBUG, f"Resolved UI file: {resolved_ui_file}")
            
            # Instantiate plugin
            instance = plugin_class(plugin_name, resolved_ui_file, signal_bus)
            
            # Initialize plugin
            instance.initialize()
            
            # Store plugin instance
            key = f"{category}.{plugin_name}"
            self.plugin_instances[key] = instance
            
            self.logger.context(self.logger.INFO, f"Plugin loaded successfully: {key}")
            return instance
            
        except ImportError as e:
            self.logger.context(self.logger.ERROR, f"Failed to import plugin module {module_path}: {str(e)}")
            return None
        except AttributeError as e:
            self.logger.context(self.logger.ERROR, f"Plugin class not found: {str(e)}")
            return None
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Failed to load plugin {category}.{plugin_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def resolve_ui_file_path(self, category, plugin_name, ui_file):
        """Resolve UI file path
        
        Args:
            category: Plugin category
            plugin_name: Plugin name
            ui_file: UI file path configuration
            
        Returns:
            Resolved absolute path to UI file
        """
        # If already an absolute path, return directly
        if os.path.isabs(ui_file):
            return ui_file
        
        # Try multiple possible paths
        possible_paths = [
            ui_file,  # Original path
            os.path.join("plugins", category, plugin_name, ui_file),  # Under plugin directory
            os.path.join("plugins", ui_file),  # Under plugins directory
            os.path.join(os.path.dirname(__file__), "..", ui_file),  # Relative to project root
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        # If not found, return original path (will cause error later)
        return ui_file
    
    def get_plugin(self, category, plugin_name):
        """Get loaded plugin instance
        
        Args:
            category: Plugin category
            plugin_name: Plugin name
            
        Returns:
            Plugin instance or None
        """
        key = f"{category}.{plugin_name}"
        return self.plugin_instances.get(key)
    
    def get_all_plugins(self):
        """Get all loaded plugin instances
        
        Returns:
            Dictionary of plugin instances
        """
        return self.plugin_instances.copy()
    
    def unload_plugin(self, category, plugin_name):
        """Unload specified plugin
        
        Args:
            category: Plugin category
            plugin_name: Plugin name
        """
        key = f"{category}.{plugin_name}"
        
        if key in self.plugin_instances:
            instance = self.plugin_instances[key]
            if hasattr(instance, 'cleanup'):
                instance.cleanup()
            del self.plugin_instances[key]
            
            # Remove from loaded modules
            module_path = f"plugins.{category}.{plugin_name}.plugin"
            if module_path in self.loaded_modules:
                del self.loaded_modules[module_path]
            
            self.logger.context(self.logger.INFO, f"Plugin unloaded: {key}")
    
    def unload_all(self):
        """Unload all plugins"""
        for key in list(self.plugin_instances.keys()):
            category, plugin_name = key.split('.')
            self.unload_plugin(category, plugin_name)
        self.logger.context(self.logger.INFO, "All plugins unloaded")
    
    def reload_plugin(self, category, plugin_name, ui_file, signal_bus):
        """Reload plugin
        
        Args:
            category: Plugin category
            plugin_name: Plugin name
            ui_file: UI file path
            signal_bus: Signal bus instance
            
        Returns:
            New plugin instance or None
        """
        # First unload old plugin
        self.unload_plugin(category, plugin_name)
        
        # Load new plugin
        return self.load_plugin(category, plugin_name, ui_file, signal_bus)