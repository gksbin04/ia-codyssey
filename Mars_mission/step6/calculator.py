import sys
from decimal import Decimal, InvalidOperation
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.last_operator = None
        self.last_operand = None
        self.new_input_expected = False

        # 버튼 위젯을 저장하여 스타일을 동적으로 변경하기 위한 딕셔너리
        self.operator_buttons = {}

        # 버튼 기본 스타일 정의
        self.style_number = (
            'QPushButton { background-color: #333333; color: white; '
            'border-radius: 35px; font-size: 28px; } '
            'QPushButton:pressed { background-color: #737373; }'
        )
        self.style_zero = (
            'QPushButton { background-color: #333333; color: white; '
            'border-radius: 35px; font-size: 28px; text-align: left; '
            'padding-left: 30px; } '
            'QPushButton:pressed { background-color: #737373; }'
        )
        self.style_operator = (
            'QPushButton { background-color: #FF9F0A; color: white; '
            'border-radius: 35px; font-size: 32px; } '
            'QPushButton:pressed { background-color: #FCC78F; }'
        )
        self.style_operator_active = (
            'QPushButton { background-color: white; color: #FF9F0A; '
            'border-radius: 35px; font-size: 32px; }'
        )
        self.style_function = (
            'QPushButton { background-color: #A5A5A5; color: black; '
            'border-radius: 35px; font-size: 24px; } '
            'QPushButton:pressed { background-color: #D9D9D9; }'
        )

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')
        self.resize(350, 500)
        self.setStyleSheet('background-color: black;')

        vbox = QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)

        self.display = QLineEdit('0')
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet(
            'font-size: 60px; padding: 10px; '
            'border: none; background-color: black; color: white;'
        )
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

        for btn_data in buttons:
            text = btn_data[0]
            row = btn_data[1]
            col = btn_data[2]
            btn_type = btn_data[3]

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
        vbox.setStretch(0, 1)
        vbox.setStretch(1, 4)

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
                    self.display.setText('0')
                    self.current_input = ''
                else:
                    self.display.setText(self.current_input)

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

    def format_result(self, val_str):
        # 불필요한 소수점 이하의 0을 제거하는 포맷팅 함수 (1E+1 방지)
        if '.' in val_str and 'e' not in val_str.lower():
            val_str = val_str.rstrip('0').rstrip('.')

        # 길이가 9자리를 초과하면 지수 표기법으로 변환
        digits_only = val_str.replace('.', '').replace('-', '')
        if len(digits_only) > 9:
            try:
                # 안전하게 변환 가능한 경우만 지수 표기 적용
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

        self.display.setText(self.current_input)

    def handle_clear(self):
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.new_input_expected = False
        self.display.setText('0')
        self.update_operator_styles(None)

    def handle_sign(self):
        current_text = self.display.text()
        if current_text == '0' or current_text == 'Error':
            return

        if current_text.startswith('-'):
            new_text = current_text[1:]
        else:
            new_text = '-' + current_text

        self.display.setText(new_text)
        # 결과값에 대해서 부호를 바꾼 것이라면, current_input도 동기화
        self.current_input = new_text

    def handle_percent(self):
        try:
            val = Decimal(self.display.text()) / Decimal('100')
            result_str = self.format_result(str(val))
            self.display.setText(result_str)
            self.current_input = result_str
            self.new_input_expected = True
        except InvalidOperation:
            pass

    def handle_operator(self, text):
        # 방금 연산자를 눌렀는데 또 다른 연산자를 누른 경우 연산자만 교체
        if self.new_input_expected and self.operator:
            self.operator = text
            self.last_operator = text
            self.update_operator_styles(text)
            return

        if self.operator:
            self.calculate_result()

        self.previous_input = self.display.text()
        self.operator = text
        self.last_operator = text
        self.new_input_expected = True
        self.update_operator_styles(text)

    def calculate_result(self):
        self.update_operator_styles(None)

        if self.operator:
            # 새로운 계산
            try:
                num1 = Decimal(self.previous_input)
                num2 = Decimal(self.display.text())
                self.last_operand = num2
            except InvalidOperation:
                return
        elif self.last_operator and self.last_operand is not None:
            # '=' 버튼 연속 누름 (이전 연산 반복)
            try:
                num1 = Decimal(self.display.text())
                num2 = self.last_operand
                self.operator = self.last_operator
            except InvalidOperation:
                return
        else:
            # 연산자 없이 '=' 누른 경우
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
                    self.display.setText('Error')
                    self.new_input_expected = True
                    self.operator = None
                    return

            result_str = self.format_result(str(result))

            self.current_input = result_str
            self.display.setText(self.current_input)
            self.previous_input = result_str
            self.new_input_expected = True

            # 다음 입력을 위해 현재 operator 초기화 (단, last_operator는 유지)
            self.operator = None

        except InvalidOperation:
            self.display.setText('Error')
            self.new_input_expected = True
            self.operator = None


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Calculator()
    ex.show()
    sys.exit(app.exec_())
