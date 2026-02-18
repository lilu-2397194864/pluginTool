import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from plugins.base_plugin import BasePlugin
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QLineEdit, QGridLayout, QWidget


class CalculatorPlugin(BasePlugin):
    """Calculator Plugin (simplified version)"""
    
    def __init__(self, plugin_name, ui_file, signal_bus):
        super().__init__(plugin_name, ui_file, signal_bus)
        self.current_input = ""
        self.operation = ""
        self.first_number = 0
    
    def initialize(self):
        """Initialize calculator plugin"""
        # Try to load UI file, create built-in UI if fails
        if not self.load_ui():
            self.create_calculator_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Send initialization complete message
        self.send_message("main_window", {
            'type': 'status',
            'message': f'{self.plugin_name} plugin initialized'
        })
        
        self.logger.context(self.logger.INFO, "Calculator plugin initialized successfully")
    
    def create_calculator_ui(self):
        """Create calculator UI"""
        self.widget = QWidget()
        layout = QVBoxLayout(self.widget)
        
        # Title
        title = QLabel("Simple Calculator")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Display box
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("font-size: 16px; padding: 5px;")
        layout.addWidget(self.display)
        
        # Button grid
        grid_layout = QGridLayout()
        
        # Button definitions
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2), ('/', 0, 3),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('*', 1, 3),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2), ('-', 2, 3),
            ('0', 3, 0), ('.', 3, 1), ('=', 3, 2), ('+', 3, 3),
            ('C', 4, 0), ('CE', 4, 1)
        ]
        
        # Create buttons
        self.buttons = {}
        for text, row, col in buttons:
            button = QPushButton(text)
            button.setFixedSize(60, 40)
            button.clicked.connect(lambda checked, t=text: self.button_clicked(t))
            grid_layout.addWidget(button, row, col)
            self.buttons[text] = button
        
        layout.addLayout(grid_layout)
        
        # Assign widget to ui for unified handling
        self.ui = type('UI', (), {})()
        self.ui.display = self.display
        
        self.logger.context(self.logger.INFO, "Built-in calculator UI created")
        return True
    
    def connect_signals(self):
        """Connect signal slots"""
        # Signals already connected during button creation
        self.logger.context(self.logger.DEBUG, "Calculator buttons connected")
        pass
    
    def button_clicked(self, text):
        """Button click handler"""
        if text in '0123456789.':
            self.current_input += text
            self.display.setText(self.current_input)
            self.logger.context(self.logger.DEBUG, f"Input: {self.current_input}")
        
        elif text in '+-*/':
            if self.current_input:
                self.first_number = float(self.current_input)
                self.operation = text
                self.current_input = ""
                self.logger.context(self.logger.DEBUG, f"Operation: {text}, first number: {self.first_number}")
        
        elif text == '=':
            if self.current_input and self.operation:
                second_number = float(self.current_input)
                result = self.calculate(self.first_number, second_number, self.operation)
                self.display.setText(str(result))
                self.current_input = str(result)
                self.operation = ""
                self.logger.context(self.logger.INFO, f"Calculation: {self.first_number} {self.operation} {second_number} = {result}")
        
        elif text == 'C':
            self.current_input = ""
            self.operation = ""
            self.first_number = 0
            self.display.setText("")
            self.logger.context(self.logger.DEBUG, "Calculator cleared")
        
        elif text == 'CE':
            self.current_input = ""
            self.display.setText("")
            self.logger.context(self.logger.DEBUG, "Current entry cleared")
    
    def calculate(self, a, b, op):
        """Perform calculation"""
        try:
            if op == '+':
                return a + b
            elif op == '-':
                return a - b
            elif op == '*':
                return a * b
            elif op == '/':
                return a / b if b != 0 else "Error"
            return 0
        except Exception as e:
            self.logger.context(self.logger.ERROR, f"Calculation error: {str(e)}")
            return "Error"
    
    def on_message(self, sender, data):
        """Receive messages from other plugins"""
        message_type = data.get('type', '')
        
        self.logger.context(self.logger.DEBUG, f"Received message type: {message_type} from {sender}")
        
        if message_type == 'calculate':
            # Handle calculation request
            expression = data.get('expression', '')
            try:
                result = eval(expression)
                self.send_message(sender, {
                    'type': 'calculation_result',
                    'result': result,
                    'request_id': data.get('request_id', '')
                })
                self.logger.context(self.logger.INFO, f"Calculated: {expression} = {result}")
            except Exception as e:
                self.send_message(sender, {
                    'type': 'calculation_result',
                    'result': f"Error: Invalid expression - {str(e)}",
                    'request_id': data.get('request_id', '')
                })
                self.logger.context(self.logger.ERROR, f"Calculation failed: {expression} - {str(e)}")
        
        elif message_type == 'status_query':
            # Respond to status query
            self.send_message(sender, {
                'type': 'status_response',
                'plugin': self.plugin_name,
                'status': 'running',
                'display': self.display.text()
            })
            self.logger.context(self.logger.DEBUG, "Responded to status query")
    
    def cleanup(self):
        """Clean up plugin resources"""
        super().cleanup()
        self.logger.context(self.logger.INFO, "Calculator plugin cleanup complete")