class CalculatorController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.input_signal.connect(self.handle_input)

    def handle_input(self, char):
        """View에서 전달받은 사용자 입력을 Model의 기능과 매핑하여 지시합니다."""
        if char in '0123456789.':
            self.model.input_character(char)
        elif char == 'AC':
            self.model.reset()
        elif char == '+/-':
            self.model.negative_positive()
        elif char == '%':
            self.model.percent()
        elif char == '+':
            self.model.add()
        elif char == '-':
            self.model.subtract()
        elif char in ('×', '*'):
            self.model.multiply()
        elif char in ('÷', '/'):
            self.model.divide()
        elif char in ('=', '\r', '\n'):
            self.model.equal()
        elif char == 'BS' or char == '\b':
            self.model.backspace()

        self.update_view()

    def update_view(self):
        """Model에게 화면에 표시할 데이터를 요청하고, View에게 그려달라고 지시합니다."""
        self.view.update_display(self.model.get_display_value())
        self.view.update_expression(self.model.get_expression())
        self.view.set_active_operator(self.model.get_active_operator())