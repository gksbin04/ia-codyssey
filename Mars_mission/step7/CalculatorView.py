from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics
import styles

class CalculatorView(QWidget):
    input_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.operator_buttons = {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')
        self.setFixedSize(styles.Dimensions.WIN_WIDTH, styles.Dimensions.WIN_HEIGHT)
        self.setStyleSheet(styles.StyleSheets.MAIN_WINDOW)

        vbox = QVBoxLayout()
        self.expr_label = QLineEdit('')
        self.expr_label.setReadOnly(True)
        self.expr_label.setAlignment(Qt.AlignRight)
        self.expr_label.setStyleSheet(styles.StyleSheets.EXPR)
        vbox.addWidget(self.expr_label)

        self.display = QLineEdit('0')
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet(styles.StyleSheets.DISPLAY)
        self.display.setFont(QFont('Arial', styles.Fonts.DISPLAY))
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.display.setFixedHeight(styles.Dimensions.DISPLAY_HEIGHT)
        vbox.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(styles.Dimensions.SPACING)
        buttons = [
            ('AC', 0, 0, 'function'), ('+/-', 0, 1, 'function'), ('%', 0, 2, 'function'), ('÷', 0, 3, 'operator'),
            ('7', 1, 0, 'number'), ('8', 1, 1, 'number'), ('9', 1, 2, 'number'), ('×', 1, 3, 'operator'),
            ('4', 2, 0, 'number'), ('5', 2, 1, 'number'), ('6', 2, 2, 'number'), ('-', 2, 3, 'operator'),
            ('1', 3, 0, 'number'), ('2', 3, 1, 'number'), ('3', 3, 2, 'number'), ('+', 3, 3, 'operator'),
            ('0', 4, 0, 'number_zero'), ('.', 4, 2, 'number'), ('=', 4, 3, 'operator_eq')
        ]

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

        vbox.addLayout(grid)
        vbox.setStretch(2, 4)
        self.setLayout(vbox)

    def on_button_click(self):
        self.input_signal.emit(self.sender().text())

    def keyPressEvent(self, event):
        key_code = event.key()
        text = event.text()
        
        if key_code in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Equal):
            self.input_signal.emit('=')
        elif key_code == Qt.Key_Escape:
            self.input_signal.emit('AC')
        elif key_code == Qt.Key_Backspace:
            self.input_signal.emit('BS')
        elif text:
            self.input_signal.emit(text)

    def update_display(self, formatted_text):
        # 렌더링 타이밍 이슈 방지를 위해 윈도우 상수를 기반으로 안전한 최대 너비 계산
        max_w = styles.Dimensions.WIN_WIDTH - 60 
        current_size = styles.Fonts.DISPLAY
        font = QFont('Arial', current_size)
        
        # 텍스트 너비가 디스플레이를 초과하면 화면에 들어올 때까지 폰트 크기를 줄임 (최소 5px)
        while QFontMetrics(font).horizontalAdvance(formatted_text) > max_w and current_size > 5:
            current_size -= 2
            font.setPointSize(current_size)
            
        self.display.setFont(font)
        self.display.setText(formatted_text)

    def update_expression(self, text):
        self.expr_label.setText(text)

    def set_active_operator(self, active_op):
        for op, btn in self.operator_buttons.items():
            if op == active_op:
                btn.setStyleSheet(styles.StyleSheets.OP_ACTIVE)
            else:
                btn.setStyleSheet(styles.StyleSheets.OPERATOR)