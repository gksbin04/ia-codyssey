import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit, QSizePolicy
from PyQt5.QtCore import Qt


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')
        self.resize(350, 500)

        vbox = QVBoxLayout()

        self.display = QLineEdit('0')
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet('font-size: 48px; padding: 10px; border: none; background-color: #f0f0f0;')
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vbox.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(5)

        buttons = [
            ('AC', 0, 0), ('+/-', 0, 1), ('%', 0, 2), ('÷', 0, 3),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('×', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('-', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3),
            ('0', 4, 0, 1, 2), ('.', 4, 2), ('=', 4, 3)
        ]

        for button_info in buttons:
            text = button_info[0]
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setStyleSheet('font-size: 24px;')
            btn.clicked.connect(self.on_button_click)

            if len(button_info) == 3:
                grid.addWidget(btn, button_info[1], button_info[2])
            else:
                grid.addWidget(btn, button_info[1], button_info[2], button_info[3], button_info[4])

        for i in range(5):
            grid.setRowStretch(i, 1)

        vbox.addLayout(grid)
        vbox.setStretch(0, 1)
        vbox.setStretch(1, 4)
        
        self.setLayout(vbox)

    def on_button_click(self):
        sender = self.sender()
        text = sender.text()

        if text in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.']:
            if text == '.' and '.' in self.current_input:
                return

            if self.current_input == '0' and text != '.':
                self.current_input = text
            else:
                self.current_input += text

            self.display.setText(self.current_input)

        elif text == 'AC':
            self.current_input = ''
            self.previous_input = ''
            self.operator = None
            self.display.setText('0')

        elif text == '+/-':
            if self.current_input:
                if self.current_input.startswith('-'):
                    self.current_input = self.current_input[1:]
                else:
                    self.current_input = '-' + self.current_input
                self.display.setText(self.current_input)
            elif self.display.text() not in ['0', 'Error']:
                current_text = self.display.text()
                if current_text.startswith('-'):
                    self.display.setText(current_text[1:])
                else:
                    self.display.setText('-' + current_text)
                self.previous_input = self.display.text()

        elif text == '%':
            if self.current_input:
                self.current_input = str(float(self.current_input) / 100)
                self.display.setText(self.current_input)
            elif self.display.text() not in ['0', 'Error']:
                current_val = str(float(self.display.text()) / 100)
                self.display.setText(current_val)
                self.previous_input = current_val

        elif text in ['+', '-', '×', '÷']:
            if self.current_input:
                if self.previous_input and self.operator:
                    self.calculate_result()
                else:
                    self.previous_input = self.current_input
                self.current_input = ''
            self.operator = text

        elif text == '=':
            self.calculate_result()
            self.operator = None

    def calculate_result(self):
        if self.previous_input and self.current_input and self.operator:
            try:
                num1 = float(self.previous_input)
                num2 = float(self.current_input)
                result = 0

                if self.operator == '+':
                    result = num1 + num2
                elif self.operator == '-':
                    result = num1 - num2
                elif self.operator == '×':
                    result = num1 * num2
                elif self.operator == '÷':
                    if num2 != 0:
                        result = num1 / num2
                    else:
                        self.display.setText('Error')
                        self.current_input = ''
                        self.previous_input = ''
                        self.operator = None
                        return

                if isinstance(result, float) and result.is_integer():
                    result = int(result)

                self.current_input = str(result)
                self.display.setText(self.current_input)
                self.previous_input = self.current_input
                self.current_input = ''

            except Exception:
                self.display.setText('Error')
                self.current_input = ''
                self.previous_input = ''
                self.operator = None


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Calculator()
    ex.show()
    sys.exit(app.exec_())
