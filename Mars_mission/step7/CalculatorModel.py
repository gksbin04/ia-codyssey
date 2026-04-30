from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

class CalculatorModel:
    """
    계산기의 핵심 비즈니스 로직(상태 및 수학 연산)을 담당하는 Model 클래스입니다.
    UI(View)와 완전히 분리되어 독립적으로 동작하며, 단위 테스트가 가능합니다.
    """

    def __init__(self):
        self.reset()

    # ── 1. 상태 관리 및 초기화 ──

    def reset(self):
        self.current_input = ''
        self.previous_input = ''
        self.operator = None
        self.last_operator = None
        self.last_operand = None
        self.new_input_expected = False
        self.error_state = False
        self.expression = ''

    # ── 2. 사용자 입력 처리 ──

    def input_character(self, char):
        if self.error_state:
            self.reset()

        if char == '.':
            if '.' in self.current_input and not self.new_input_expected:
                return
            if self.new_input_expected or not self.current_input:
                self.current_input = '0.'
                self.new_input_expected = False
                return

        if self.new_input_expected:
            self.current_input = ''
            self.new_input_expected = False

        if self.current_input == '0' and char != '.':
            self.current_input = char
        else:
            self.current_input += char

    # ── 3. 부가 기능 (명세 메소드) ──

    def negative_positive(self):
        if self.error_state:
            self.reset()
            return
        target = self.current_input or self.previous_input
        if not target or target == '0':
            return
        
        if target.startswith('-'):
            self.current_input = target[1:]
        else:
            self.current_input = '-' + target

    def percent(self):
        if self.error_state:
            self.reset()
            return
        target = self.current_input or self.previous_input or '0'
        try:
            val = Decimal(target) / Decimal('100')
            # 퍼센트 계산 시에도 깔끔하게 반올림 및 정규화 적용
            val = round(val, 6).normalize()
            self.current_input = self._format_result(str(val))
            self.new_input_expected = True
        except InvalidOperation:
            self.error_state = True

    # ── 4. 사칙연산 (명세 메소드) ──

    def add(self):
        self.set_operator('+')

    def subtract(self):
        self.set_operator('-')

    def multiply(self):
        self.set_operator('×')

    def divide(self):
        self.set_operator('÷')

    def equal(self):
        self.calculate()

    def backspace(self):
        if self.error_state:
            self.reset()
            return
        if self.current_input and not self.new_input_expected:
            self.current_input = self.current_input[:-1]
            if not self.current_input or self.current_input == '-':
                self.current_input = ''

    # ── 5. 내부 연산 엔진 ──

    def set_operator(self, op):
        if self.error_state:
            self.reset()
            return

        if self.new_input_expected and self.operator:
            self.operator = op
            self.last_operator = op
            fmt_prev = self._format_for_display(self.previous_input)
            self.expression = f'{fmt_prev} {op}'
            return

        if self.operator:
            self.calculate()
            if self.error_state:
                return

        active_input = self.current_input or self.previous_input or '0'
        self.previous_input = active_input
        self.operator = op
        self.last_operator = op
        self.new_input_expected = True
        
        fmt_prev = self._format_for_display(self.previous_input)
        self.expression = f'{fmt_prev} {op}'

    def calculate(self):
        if self.error_state:
            self.reset()
            return
            
        active_input = self.current_input or self.previous_input or '0'
        
        if not self.operator:
            if self.last_operator and self.last_operand is not None:
                try:
                    num1 = Decimal(active_input)
                    num2 = self.last_operand
                    op = self.last_operator
                except InvalidOperation:
                    return
            else:
                return
        else:
            try:
                num1 = Decimal(self.previous_input)
                num2 = Decimal(active_input)
                self.last_operand = num2
                op = self.operator
            except InvalidOperation:
                return

        try:
            if op == '+':
                res = num1 + num2
            elif op == '-':
                res = num1 - num2
            elif op == '×':
                res = num1 * num2
            elif op == '÷':
                if num2 == 0:
                    raise ZeroDivisionError
                res = num1 / num2
            
            # 소수점 6자리 이하 반올림 (파이썬 내장 round가 가장 깔끔하게 처리됨)
            res = round(res, 6).normalize()

            res_str = self._format_result(str(res))
            fmt_n1 = self._format_for_display(str(num1))
            fmt_n2 = self._format_for_display(str(num2))
            
            self.expression = f'{fmt_n1} {op} {fmt_n2} ='
            self.current_input = res_str
            self.previous_input = res_str
            self.operator = None
            self.new_input_expected = True
        except (ZeroDivisionError, Exception):
            self.error_state = True

    # ── 6. 데이터 포맷팅 및 반환 ──

    def _format_result(self, val_str):
        if 'e' in val_str.lower():
            # 지수 표기법일 경우 불필요한 0 제거 (예: 1.20000e+05 -> 1.2e+05)
            base, exp = val_str.lower().split('e')
            base = base.rstrip('0').rstrip('.') if '.' in base else base
            return f'{base}e{exp}'

        if '.' in val_str:
            val_str = val_str.rstrip('0').rstrip('.')
            
        return val_str

    def _format_for_display(self, text):
        if not text or text == 'Error' or 'e' in text.lower():
            return text
        is_neg = text.startswith('-')
        body = text[1:] if is_neg else text
        if '.' in body:
            int_p, dec_p = body.split('.', 1)
            res = f'{int(int_p):,}.{dec_p}' if int_p else f'0.{dec_p}'
        else:
            res = f'{int(body):,}' if body else '0'
        return f'-{res}' if is_neg else res

    def get_display_value(self):
        if self.error_state:
            return 'Error'
        text = self.current_input or self.previous_input or '0'
        if not text:
            text = '0'
        return self._format_for_display(text)

    def get_expression(self):
        if self.error_state:
            return ''
        return self.expression

    def get_active_operator(self):
        if self.error_state:
            return None
        return self.operator if self.new_input_expected else None