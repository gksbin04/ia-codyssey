import sys
from decimal import Decimal, InvalidOperation
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics
# 디자인 상수가 정의된 외부 스타일 모듈
import styles


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        # 내부 계산을 위한 상태 변수(입력값, 대기 연산자 등) 초기화
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.last_operator = None
        self.last_operand = None
        self.new_input_expected = False
        self.operator_buttons = {}
        
        # UI 레이아웃 및 위젯 생성
        self.init_ui()

    def init_ui(self):
        # 윈도우 고유 설정 및 메인 스타일시트 적용
        self.setWindowTitle('Calculator')
        self.setFixedSize(styles.Dimensions.WIN_WIDTH, styles.Dimensions.WIN_HEIGHT)
        self.setStyleSheet(styles.StyleSheets.MAIN_WINDOW)

        # 위젯 배치를 위한 메인 수직 레이아웃
        vbox = QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)

        # 이전 연산 과정과 결과를 보여주는 상단 보조 레이블
        self.expr_label = QLineEdit('')
        self.expr_label.setReadOnly(True)
        self.expr_label.setAlignment(Qt.AlignRight)
        self.expr_label.setStyleSheet(styles.StyleSheets.EXPR)
        vbox.addWidget(self.expr_label)

        # 현재 입력값 및 최종 결과가 표시되는 메인 디스플레이
        self.display = QLineEdit('0')
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet(styles.StyleSheets.DISPLAY)
        self.display.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        vbox.addWidget(self.display)

        # 5행 4열의 아이폰 스타일 배치를 위한 그리드 레이아웃
        grid = QGridLayout()
        grid.setSpacing(styles.Dimensions.SPACING)

        # 버튼 생성 데이터: (라벨, 행, 열, 스타일타입)
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

        # 버튼 생성 및 타입별 디자인 적용 루프
        for text, row, col, btn_type in buttons:
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            if btn_type == 'number':
                btn.setStyleSheet(styles.StyleSheets.NUMBER)
            elif btn_type == 'number_zero':
                btn.setStyleSheet(styles.StyleSheets.ZERO)
            elif btn_type.startswith('operator'):
                btn.setStyleSheet(styles.StyleSheets.OPERATOR)
                # 사칙연산 버튼은 강조 효과를 위해 별도 저장
                if text in ['+', '-', '×', '÷']:
                    self.operator_buttons[text] = btn
            elif btn_type == 'function':
                btn.setStyleSheet(styles.StyleSheets.FUNCTION)

            btn.clicked.connect(self.on_button_click)

            # '0' 버튼은 레이아웃 2칸을 점유하도록 설정
            if text == '0':
                grid.addWidget(btn, row, col, 1, 2)
            else:
                grid.addWidget(btn, row, col)

        # 각 행이 일정한 비율로 늘어나도록 설정
        for i in range(5):
            grid.setRowStretch(i, 1)

        vbox.addLayout(grid)
        vbox.setStretch(1, 1)
        vbox.setStretch(2, 4)

        self.setLayout(vbox)

    def keyPressEvent(self, event):
        # 키보드 물리 키 입력을 숫자, 연산, 엔터 등의 기능으로 매핑
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
        elif event.key() == Qt.Key_Escape:
            self.handle_clear()
        elif event.key() == Qt.Key_Backspace:
            self.handle_backspace()

    def handle_backspace(self):
        # 마지막 입력 문자를 지우고, 값이 없으면 '0'으로 디폴트 처리
        if self.current_input and not self.new_input_expected:
            self.current_input = self.current_input[:-1]
            if not self.current_input or self.current_input == '-':
                self.update_display('0')
                self.current_input = ''
            else:
                self.update_display(self.current_input)

    def on_button_click(self):
        # 화면의 버튼 클릭 시 텍스트를 판별하여 해당 기능 실행
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
        # 선택된 연산자 버튼의 색상을 반전시켜 현재 상태를 시각화
        for op, btn in self.operator_buttons.items():
            if op == active_op:
                btn.setStyleSheet(styles.StyleSheets.OP_ACTIVE)
            else:
                btn.setStyleSheet(styles.StyleSheets.OPERATOR)

    def format_for_display(self, text):
        # 숫자를 천 단위 콤마와 부호가 포함된 가시적인 텍스트로 변환
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
        # 화면을 갱신하며, 글자 길이에 맞춰 폰트 크기를 자동으로 축소 조절
        formatted = self.format_for_display(text)
        
        # 디스플레이 너비에 맞춘 폰트 스케일링 로직
        max_w = self.display.width() - 60 
        current_size = styles.Fonts.DISPLAY
        
        while current_size > 15:
            font = QFont('Arial', current_size)
            metrics = QFontMetrics(font)
            if metrics.horizontalAdvance(formatted) < max_w:
                break
            current_size -= 2

        self.display.setFont(QFont('Arial', current_size))
        self.display.setText(formatted)

    def format_result(self, val_str):
        # 결과값의 불필요한 소수점을 제거하고 9자리 초과 시 지수 표기법 적용
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
        # 숫자 및 소수점의 연속 입력을 처리하며 자리수 제한(9자) 적용
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
        # 메모리에 저장된 모든 수치와 연산자 상태를 초기화(AC)
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.new_input_expected = False
        self.update_display('0')
        self.expr_label.setText('')
        self.update_operator_styles(None)

    def handle_sign(self):
        # 현재 화면에 표시된 숫자의 양수/음수 부호를 즉시 반전
        raw_text = self.current_input or self.previous_input
        if not raw_text or raw_text == '0':
            return

        new_text = raw_text[1:] if raw_text.startswith('-') else '-' + raw_text
        self.current_input = new_text
        self.update_display(new_text)

    def handle_percent(self):
        # 현재 숫자를 백분율(1/100)로 계산하여 결과 도출
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
        # 연산자 선택 시 현재 값을 대기시키거나 중간 연산을 수행
        if self.new_input_expected and self.operator:
            self.operator = text
            self.last_operator = text
            self.update_operator_styles(text)
            fmt_prev = self.format_for_display(self.previous_input)
            self.expr_label.setText(f'{fmt_prev} {text}')
            return

        if self.operator:
            self.calculate_result()

        active_input = self.current_input or self.previous_input or '0'
        self.previous_input = active_input
        self.operator = text
        self.last_operator = text
        self.new_input_expected = True
        self.update_operator_styles(text)
        fmt_prev = self.format_for_display(self.previous_input)
        self.expr_label.setText(f'{fmt_prev} {text}')

    def calculate_result(self):
        # Decimal을 사용하여 정밀한 최종 계산을 수행하고 수식 레이블 업데이트
        self.update_operator_styles(None)
        active_input = self.current_input or self.previous_input or '0'
        
        # 연산자 대기 유무에 따른 수치 할당
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
            # 사칙연산 실행 및 0으로 나누기 예외 처리
            if op == '+': res = num1 + num2
            elif op == '-': res = num1 - num2
            elif op == '×': res = num1 * num2
            elif op == '÷':
                if num2 == 0:
                    self.update_display('Error')
                    self.handle_clear()
                    return
                res = num1 / num2
            
            # 최종 결과 포맷팅 및 상태 저장
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
