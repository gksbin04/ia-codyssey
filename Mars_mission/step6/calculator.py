import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_value = '0'
        self.first_num = None
        self.operator = None
        self.is_typing = False
        self.init_ui()

    def init_ui(self):
        vbox = QVBoxLayout()
        self.setStyleSheet('background-color: black;')

        self.display = QLabel('0')
        self.display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.display.setStyleSheet('color: white; padding: 10px;')
        self.display.setFont(QFont('Arial', 50))
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        vbox.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(10)

        buttons = [
            ('AC', 0, 0, 1), ('+/-', 0, 1, 1), ('%', 0, 2, 1), ('÷', 0, 3, 1),
            ('7', 1, 0, 1), ('8', 1, 1, 1), ('9', 1, 2, 1), ('×', 1, 3, 1),
            ('4', 2, 0, 1), ('5', 2, 1, 1), ('6', 2, 2, 1), ('-', 2, 3, 1),
            ('1', 3, 0, 1), ('2', 3, 1, 1), ('3', 3, 2, 1), ('+', 3, 3, 1),
            ('0', 4, 0, 2), ('.', 4, 2, 1), ('=', 4, 3, 1)
        ]

        for info in buttons:
            text = info[0]
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setFont(QFont('Arial', 20))
            
            if text in ['÷', '×', '-', '+', '=']:
                btn.setStyleSheet('background-color: #FF9F0A; color: white; border-radius: 10px;')
            elif text in ['AC', '+/-', '%']:
                btn.setStyleSheet('background-color: #A5A5A5; color: black; border-radius: 10px;')
            else:
                btn.setStyleSheet('background-color: #333333; color: white; border-radius: 10px;')
            
            btn.clicked.connect(self.on_click)
            grid.addWidget(btn, info[1], info[2], 1, info[3])

        vbox.addLayout(grid)
        self.setLayout(vbox)
        self.setWindowTitle('Codyssey Pro Calc')
        self.resize(350, 550)

    def keyPressEvent(self, event):
        key = event.text()
        if key.isdigit() or key == '.':
            self.handle_digit(key) if key.isdigit() else self.handle_decimal()
        elif key == '+':
            self.handle_operator('+')
        elif key == '-':
            self.handle_operator('-')
        elif key == '*':
            self.handle_operator('×')
        elif key == '/':
            self.handle_operator('÷')
        elif key in ['\r', '\n', '=']:
            self.calculate()
        elif event.key() == Qt.Key_Escape:
            self.clear_all()
        elif event.key() == Qt.Key_Backspace:
            self.handle_backspace()
        self.update_display()

    def on_click(self):
        key = self.sender().text()
        if key.isdigit():
            self.handle_digit(key)
        elif key == 'AC':
            self.clear_all()
        elif key == '.':
            self.handle_decimal()
        elif key in ['+', '-', '×', '÷']:
            self.handle_operator(key)
        elif key == '=':
            self.calculate()
        elif key == '+/-':
            self.toggle_sign()
        elif key == '%':
            self.apply_percent()
        self.update_display()

    def handle_digit(self, digit):
        if self.current_value == '0' or not self.is_typing:
            self.current_value = digit
            self.is_typing = True
        else:
            if len(self.current_value) < 12:  # 최대 입력 길이 제한
                self.current_value += digit

    def handle_backspace(self):
        if self.is_typing:
            self.current_value = self.current_value[:-1]
            if not self.current_value or self.current_value == '-':
                self.current_value = '0'

    def handle_decimal(self):
        if not self.is_typing:
            self.current_value = '0.'
            self.is_typing = True
        elif '.' not in self.current_value:
            self.current_value += '.'

    def handle_operator(self, op):
        if self.first_num is not None and self.is_typing:
            self.calculate()
        self.first_num = float(self.current_value)
        self.operator = op
        self.is_typing = False

    def calculate(self):
        if self.operator and self.first_num is not None:
            try:
                second_num = float(self.current_value)
                if self.operator == '+':
                    res = self.first_num + second_num
                elif self.operator == '-':
                    res = self.first_num - second_num
                elif self.operator == '×':
                    res = self.first_num * second_num
                elif self.operator == '÷':
                    if second_num == 0:
                        raise ZeroDivisionError
                    res = self.first_num / second_num
                
                res = round(res, 10)
                self.current_value = str(int(res)) if res == int(res) else str(res)
                self.first_num = None
                self.operator = None
                self.is_typing = False
            except (ZeroDivisionError, Exception):
                self.current_value = 'Error'
                self.is_typing = False

    def clear_all(self):
        self.current_value = '0'
        self.first_num = None
        self.operator = None
        self.is_typing = False

    def toggle_sign(self):
        if self.current_value not in ['0', 'Error']:
            if self.current_value.startswith('-'):
                self.current_value = self.current_value[1:]
            else:
                self.current_value = '-' + self.current_value

    def apply_percent(self):
        try:
            self.current_value = str(float(self.current_value) / 100)
            self.is_typing = False
        except ValueError:
            pass

    def update_display(self):
        text = self.current_value
        font_size = 50
        if len(text) > 10:
            font_size = 30
        self.display.setFont(QFont('Arial', font_size))

        if text == 'Error':
            self.display.setText(text)
            return

        try:
            if '.' in text:
                p = text.split('.')
                formatted = '{:,}.{}'.format(int(p[0]), p[1])
            else:
                formatted = '{:,}'.format(int(text))
            self.display.setText(formatted)
        except ValueError:
            self.display.setText(text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    calc = Calculator()
    calc.show()
    sys.exit(app.exec_())