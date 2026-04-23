import sys
from decimal import Decimal, InvalidOperation
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
# 스타일 모듈 임포트
import styles

class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        # 계산 상태 관리 변수 초기화
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.last_operator = None
        self.last_operand = None
        self.new_input_expected = False
        self.operator_buttons = {}
        
        # UI 초기화 메서드 호출
        self.init_ui()

    def init_ui(self):
        # 윈도우 제목 및 고정 크기 설정
        self.setWindowTitle('Calculator')
        self.setFixedSize(styles.Dimensions.WIN_WIDTH, styles.Dimensions.WIN_HEIGHT)
        self.setStyleSheet(styles.StyleSheets.MAIN_WINDOW)

        # 메인 세로 레이아웃 생성 및 마진 설정
        vbox = QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)

        # 수식 표시용 레이블 생성 및 스타일 적용
        self.expr_label = QLineEdit('')
        self.expr_label.setReadOnly(True)
        self.expr_label.setAlignment(Qt.AlignRight)
        self.expr_label.setStyleSheet(styles.StyleSheets.EXPR)
        vbox.addWidget(self.expr_label)

        # 메인 숫자 디스플레이 생성 및 스타일 적용
        self.display = QLineEdit('0')
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet(styles.StyleSheets.DISPLAY)
        self.display.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        vbox.addWidget(self.display)

        # 버튼 배치를 위한 그리드 레이아웃 생성
        grid = QGridLayout()
        grid.setSpacing(styles.Dimensions.SPACING)

        # 버튼 구성 데이터 (텍스트, 행, 열, 버튼 타입)
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

        # 버튼 생성 및 타입별 스타일 지정
        for text, row, col, btn_type in buttons:
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            if btn_type == 'number':
                btn.setStyleSheet(styles.StyleSheets.NUMBER)
            elif btn_type == 'number_zero':
                btn.setStyleSheet(styles.StyleSheets.ZERO)
            elif btn_type.startswith('operator'):
                btn.setStyleSheet(styles.StyleSheets.OPERATOR)
                if text in ['+', '-', '×', '÷']:
                    self.operator_buttons[text] = btn
            elif btn_type == 'function':
                btn.setStyleSheet(styles.StyleSheets.FUNCTION)

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
            self.handle_backspace()

    def handle_backspace(self):
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
                btn.setStyleSheet(styles.StyleSheets.OP_ACTIVE)
            else:
                btn.setStyleSheet(styles.StyleSheets.OPERATOR)

    def format_for_display(self, text):
        if not text or text == 'Error':
            return text
        if 'e' in text.lower():
            return text

        is_negative = text.startswith('-')
        body = text[1:] if is_negative else text

        if '.' in body:
            int_part, dec_part = body.split('.', 1)
            int_formatted = f'{int(int_part):,}' if int_part else '0'
            result = f'{int_formatted}.{dec_part}'
        else:
            result = f'{int(body):,}' if body else ''

        return f'-{result}' if is_negative else result

    def update_display(self, text):
        # 숫자에 천 단위 콤마 추가
        formatted = self.format_for_display(text)
        
        # [핵심 복구] 폰트 자동 스케일링 로직
        # 디스플레이 너비에서 충분한 여유 공간(60px)을 제외한 가용 너비 계산
        max_w = self.display.width() - 60 
        current_size = styles.Fonts.DISPLAY
        
        # 실제 텍스트 너비가 가용 너비보다 작아질 때까지 폰트 크기 축소
        while current_size > 15:
            font = QFont('Arial', current_size)
            metrics = QFontMetrics(font)
            if metrics.horizontalAdvance(formatted) < max_w:
                break
            current_size -= 2

        # 계산된 폰트 크기 적용 및 텍스트 설정
        self.display.setFont(QFont('Arial', current_size))
        self.display.setText(formatted)

    def format_result(self, val_str):
        if '.' in val_str and 'e' not in val_str.lower():
            val_str = val_str.rstrip('0').rstrip('.')

        digits_only = val_str.replace('.', '').replace('-', '')
        if len(digits_only) > 9:
            try:
                decimal_val = Decimal(val_str)
                val_str = f'{decimal_val:.5e}'
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
        new_text = raw_text[1:] if raw_text.startswith('-') else '-' + raw_text
        self.current_input = new_text
        self.update_display(new_text)

    def handle_percent(self):
        target = self.current_input or self.previous_input
        if not target: target = '0'
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
            self.expr_label.setText(f'{self.format_for_display(self.previous_input)} {text}')
            return
        if self.operator:
            self.calculate_result()
        active_input = self.current_input or self.previous_input or '0'
        self.previous_input = active_input
        self.operator = text
        self.last_operator = text
        self.new_input_expected = True
        self.update_operator_styles(text)
        self.expr_label.setText(f'{self.format_for_display(self.previous_input)} {text}')

    def calculate_result(self):
        self.update_operator_styles(None)
        active_input = self.current_input or self.previous_input or '0'
        if not self.operator:
            if self.last_operator and self.last_operand is not None:
                try:
                    num1, num2 = Decimal(active_input), self.last_operand
                    op = self.last_operator
                except: return
            else: return
        else:
            try:
                num1, num2 = Decimal(self.previous_input), Decimal(active_input)
                self.last_operand = num2
                op = self.operator
            except: return

        try:
            if op == '+': res = num1 + num2
            elif op == '-': res = num1 - num2
            elif op == '×': res = num1 * num2
            elif op == '÷':
                if num2 == 0:
                    self.update_display('Error')
                    self.handle_clear()
                    return
                res = num1 / num2
            
            res_str = self.format_result(str(res))
            fmt_n1 = self.format_for_display(str(num1))
            fmt_n2 = self.format_for_display(str(num2))
            self.expr_label.setText(f'{fmt_n1} {op} {fmt_n2} =')
            self.current_input = res_str
            self.previous_input = res_str
            self.update_display(res_str)
            self.operator = None
            self.new_input_expected = True
        except:
            self.update_display('Error')

def main():
    app = QApplication(sys.argv)
    calc = Calculator()
    calc.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
