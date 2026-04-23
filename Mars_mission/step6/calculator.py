import sys
from decimal import Decimal, InvalidOperation
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt

# --- 스타일 및 레이아웃 상수 정의 ---
WIN_WIDTH = 350
WIN_HEIGHT = 500

STYLE_BG_MAIN = 'background-color: black;'
STYLE_DISPLAY_MAIN = (
    'font-size: 60px; padding: 10px; '
    'border: none; background-color: black; color: white;'
)
STYLE_DISPLAY_EXPR = (
    'font-size: 20px; padding: 0 10px; '
    'border: none; background-color: black; color: #a0a0a0;'
)

COLOR_NUM_BG = '#333333'
COLOR_NUM_PRESSED = '#737373'
COLOR_NUM_TEXT = 'white'

COLOR_OP_BG = '#FF9F0A'
COLOR_OP_PRESSED = '#FCC78F'
COLOR_OP_ACTIVE_BG = 'white'
COLOR_OP_ACTIVE_TEXT = '#FF9F0A'
COLOR_OP_TEXT = 'white'

COLOR_FUNC_BG = '#A5A5A5'
COLOR_FUNC_PRESSED = '#D9D9D9'
COLOR_FUNC_TEXT = 'black'

BTN_RADIUS = 35
BTN_FONT_LARGE = 32
BTN_FONT_MEDIUM = 28
BTN_FONT_SMALL = 24


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.last_operator = None
        self.last_operand = None
        self.new_input_expected = False

        self.operator_buttons = {}

        self.style_number = (
            f'QPushButton {{ background-color: {COLOR_NUM_BG}; '
            f'color: {COLOR_NUM_TEXT}; border-radius: {BTN_RADIUS}px; '
            f'font-size: {BTN_FONT_MEDIUM}px; }} '
            f'QPushButton:pressed {{ background-color: {COLOR_NUM_PRESSED}; }}'
        )
        self.style_zero = (
            f'QPushButton {{ background-color: {COLOR_NUM_BG}; '
            f'color: {COLOR_NUM_TEXT}; border-radius: {BTN_RADIUS}px; '
            f'font-size: {BTN_FONT_MEDIUM}px; text-align: left; '
            f'padding-left: 30px; }} '
            f'QPushButton:pressed {{ background-color: {COLOR_NUM_PRESSED}; }}'
        )
        self.style_operator = (
            f'QPushButton {{ background-color: {COLOR_OP_BG}; '
            f'color: {COLOR_OP_TEXT}; border-radius: {BTN_RADIUS}px; '
            f'font-size: {BTN_FONT_LARGE}px; }} '
            f'QPushButton:pressed {{ background-color: {COLOR_OP_PRESSED}; }}'
        )
        self.style_operator_active = (
            f'QPushButton {{ background-color: {COLOR_OP_ACTIVE_BG}; '
            f'color: {COLOR_OP_ACTIVE_TEXT}; border-radius: {BTN_RADIUS}px; '
            f'font-size: {BTN_FONT_LARGE}px; }}'
        )
        self.style_function = (
            f'QPushButton {{ background-color: {COLOR_FUNC_BG}; '
            f'color: {COLOR_FUNC_TEXT}; border-radius: {BTN_RADIUS}px; '
            f'font-size: {BTN_FONT_SMALL}px; }} '
            f'QPushButton:pressed {{ '
            f'background-color: {COLOR_FUNC_PRESSED}; }}'
        )

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')
        self.setFixedSize(WIN_WIDTH, WIN_HEIGHT)
        self.setStyleSheet(STYLE_BG_MAIN)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)

        self.expr_label = QLineEdit('')
        self.expr_label.setReadOnly(True)
        self.expr_label.setAlignment(Qt.AlignRight)
        self.expr_label.setStyleSheet(STYLE_DISPLAY_EXPR)
        self.expr_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        vbox.addWidget(self.expr_label)

        self.display = QLineEdit('0')
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet(STYLE_DISPLAY_MAIN)
        self.display.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        vbox.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(10)

        buttons = [
            ('AC', 0, 0, 'function'), ('+/-', 0, 1, 'function'),
            ('%', 0, 2, 'function'), ('÷', 0, 3, 'operator'),
            ('7', 1, 0, 'number'), ('8', 1, 1, 'number'),
            ('9', 1, 2, 'number'), ('×', 1, 3, 'operator'),
            ('4', 2, 0, 'number'), ('5', 2, 1, 'number'),
            ('6', 2, 2, 'number'), ('-', 2, 3, 'operator'),
            ('1', 3, 0, 'number'), ('2', 3, 1, 'number'),
            ('3', 3, 2, 'number'), ('+', 3, 3, 'operator'),
            ('0', 4, 0, 'number_zero'), ('.', 4, 2, 'number'),
            ('=', 4, 3, 'operator_eq')
        ]

        for text, row, col, btn_type in buttons:
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            if btn_type == 'number':
                btn.setStyleSheet(self.style_number)
            elif btn_type == 'number_zero':
                btn.setStyleSheet(self.style_zero)
            elif btn_type.startswith('operator'):
                btn.setStyleSheet(self.style_operator)
                if text in ['+', '-', '×', '÷']:
                    self.operator_buttons[text] = btn
            elif btn_type == 'function':
                btn.setStyleSheet(self.style_function)

            btn.clicked.connect(self.on_button_click)

            if text == '0':
                grid.addWidget(btn, row, col, 1, 2)
            else:
                grid.addWidget(btn, row, col)

        for i in range(5):
            grid.setRowStretch(i, 1)

        vbox.addLayout(grid)
        vbox.setStretch(1, 1)
        vbox.setStretch(2, 4)

        self.setLayout(vbox)

    def keyPressEvent(self, event):
        key = event.text()
        if key in '0123456789.':
            self.handle_number(key)
        elif key in '+-':
            self.handle_operator(key)
        elif key == '*':
            self.handle_operator('×')
        elif key == '/':
            self.handle_operator('÷')
        elif key == '%' or event.key() == Qt.Key_Percent:
            self.handle_percent()
        elif event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Equal):
            self.calculate_result()
        elif event.key() in (Qt.Key_Escape, Qt.Key_Clear):
            self.handle_clear()
        elif event.key() == Qt.Key_Backspace:
            if self.current_input and not self.new_input_expected:
                self.current_input = self.current_input[:-1]
                if not self.current_input or self.current_input == '-':
                    self.update_display('0')
                    self.current_input = ''
                else:
                    self.update_display(self.current_input)

    def on_button_click(self):
        sender = self.sender()
        text = sender.text()

        if text in '0123456789.':
            self.handle_number(text)
        elif text == 'AC':
            self.handle_clear()
        elif text == '+/-':
            self.handle_sign()
        elif text == '%':
            self.handle_percent()
        elif text in ('+', '-', '×', '÷'):
            self.handle_operator(text)
        elif text == '=':
            self.calculate_result()

    def update_operator_styles(self, active_op=None):
        for op, btn in self.operator_buttons.items():
            if op == active_op:
                btn.setStyleSheet(self.style_operator_active)
            else:
                btn.setStyleSheet(self.style_operator)

    def format_for_display(self, text):
        if not text or text == 'Error':
            return text
        if 'e' in text.lower():
            return text

        is_negative = text.startswith('-')
        body = text[1:] if is_negative else text

        if '.' in body:
            int_part, dec_part = body.split('.', 1)
            int_formatted = f"{int(int_part):,}" if int_part else "0"
            result = f"{int_formatted}.{dec_part}"
        else:
            if not body:
                result = ""
            else:
                result = f"{int(body):,}"

        return f"-{result}" if is_negative else result

    def update_display(self, text):
        self.display.setText(self.format_for_display(text))

    def format_result(self, val_str):
        if '.' in val_str and 'e' not in val_str.lower():
            val_str = val_str.rstrip('0').rstrip('.')

        digits_only = val_str.replace('.', '').replace('-', '')
        if len(digits_only) > 9:
            try:
                decimal_val = Decimal(val_str)
                val_str = f"{decimal_val:.5e}"
            except InvalidOperation:
                pass

        return val_str

    def handle_number(self, text):
        self.update_operator_styles(None)

        if self.new_input_expected:
            self.current_input = ''
            self.new_input_expected = False

        if text == '.' and '.' in self.current_input:
            return

        digits_only = self.current_input.replace('.', '').replace('-', '')
        if len(digits_only) >= 9:
            return

        if self.current_input == '0' and text != '.':
            self.current_input = text
        else:
            self.current_input += text

        self.update_display(self.current_input)

    def handle_clear(self):
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.new_input_expected = False
        self.update_display('0')
        self.expr_label.setText('')
        self.update_operator_styles(None)

    def handle_sign(self):
        raw_text = self.current_input or self.previous_input
        if not raw_text or raw_text == '0':
            return

        if raw_text.startswith('-'):
            new_text = raw_text[1:]
        else:
            new_text = '-' + raw_text

        self.current_input = new_text
        self.update_display(new_text)

    def handle_percent(self):
        target = self.current_input or self.previous_input
        if not target:
            target = '0'

        try:
            val = Decimal(target) / Decimal('100')
            result_str = self.format_result(str(val))
            self.current_input = result_str
            self.update_display(result_str)
            self.new_input_expected = True
        except InvalidOperation:
            pass

    def handle_operator(self, text):
        if self.new_input_expected and self.operator:
            self.operator = text
            self.last_operator = text
            self.update_operator_styles(text)
            fmt_prev = self.format_for_display(self.previous_input)
            self.expr_label.setText(f"{fmt_prev} {text}")
            return

        if self.operator:
            self.calculate_result()

        active_input = self.current_input or self.previous_input
        if not active_input:
            active_input = '0'

        self.previous_input = active_input
        self.operator = text
        self.last_operator = text
        self.new_input_expected = True
        self.update_operator_styles(text)
        fmt_prev = self.format_for_display(self.previous_input)
        self.expr_label.setText(f"{fmt_prev} {text}")

    def calculate_result(self):
        self.update_operator_styles(None)

        expr_text = ""
        active_input = self.current_input or self.previous_input
        if not active_input:
            active_input = '0'

        if self.operator:
            try:
                num1 = Decimal(self.previous_input)
                num2 = Decimal(active_input)
                self.last_operand = num2
                fmt_active = self.format_for_display(active_input)
                expr_text = (
                    f"{self.format_for_display(self.previous_input)} "
                    f"{self.operator} {fmt_active} ="
                )
            except InvalidOperation:
                return
        elif self.last_operator and self.last_operand is not None:
            try:
                num1 = Decimal(active_input)
                num2 = self.last_operand
                self.operator = self.last_operator
                fmt_num2 = self.format_for_display(str(num2))
                expr_text = (
                    f"{self.format_for_display(active_input)} "
                    f"{self.operator} {fmt_num2} ="
                )
            except InvalidOperation:
                return
        else:
            return

        try:
            result = Decimal('0')

            if self.operator == '+':
                result = num1 + num2
            elif self.operator == '-':
                result = num1 - num2
            elif self.operator == '×':
                result = num1 * num2
            elif self.operator == '÷':
                if num2 != Decimal('0'):
                    result = num1 / num2
                else:
                    self.update_display('Error')
                    self.new_input_expected = True
                    self.operator = None
                    self.expr_label.setText('')
                    return

            result_str = self.format_result(str(result))

            self.current_input = result_str
            self.update_display(self.current_input)
            self.previous_input = result_str
            self.new_input_expected = True

            self.expr_label.setText(expr_text)
            self.operator = None

        except InvalidOperation:
            self.update_display('Error')
            self.new_input_expected = True
            self.operator = None
            self.expr_label.setText('')
 

def main():
    app = QApplication(sys.argv)
    ex = Calculator()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()