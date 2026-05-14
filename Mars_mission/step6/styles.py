# --- styles.py ---

class Dimensions:
    """레이아웃 및 크기 관련 상수"""
    WIN_WIDTH = 350
    WIN_HEIGHT = 550
    BTN_RADIUS = 35
    DISPLAY_HEIGHT = 120
    SPACING = 10


class Colors:
    """색상 테마 정의"""
    BLACK = 'black'
    WHITE = 'white'
    GRAY_TEXT = '#a0a0a0'
    
    # 숫자 버튼
    NUM_BG = '#333333'
    NUM_PRESSED = '#737373'
    
    # 연산 버튼
    OP_BG = '#FF9F0A'
    OP_PRESSED = '#FCC78F'
    OP_ACTIVE_BG = 'white'
    OP_ACTIVE_TEXT = '#FF9F0A'
    
    # 상단 기능 버튼
    FUNC_BG = '#A5A5A5'
    FUNC_PRESSED = '#D9D9D9'


class Fonts:
    """폰트 크기 정의"""
    DISPLAY = 60
    EXPR = 20
    BTN_L = 32
    BTN_M = 28
    BTN_S = 24


class StyleSheets:
    """최종 QSS 스타일 시트 정의"""
    MAIN_WINDOW = f'background-color: {Colors.BLACK};'

    DISPLAY = (
        f'font-size: {Fonts.DISPLAY}px; padding: 10px 20px; '
        f'border: none; background-color: {Colors.BLACK}; color: {Colors.WHITE};'
    )

    EXPR = (
        f'font-size: {Fonts.EXPR}px; padding: 0 20px; '
        f'border: none; background-color: {Colors.BLACK}; color: {Colors.GRAY_TEXT};'
    )

    @staticmethod
    def get_btn_style(bg, pressed_bg, text_color, font_size, align='center', padding=0):
        return (
            f'QPushButton {{ background-color: {bg}; color: {text_color}; '
            f'border-radius: {Dimensions.BTN_RADIUS}px; font-size: {font_size}px; '
            f'text-align: {align}; padding-left: {padding}px; }} '
            f'QPushButton:pressed {{ background-color: {pressed_bg}; }}'
        )

    # 사전 정의된 버튼 스타일들
    NUMBER = get_btn_style.__func__(Colors.NUM_BG, Colors.NUM_PRESSED, Colors.WHITE, Fonts.BTN_M)
    ZERO = get_btn_style.__func__(Colors.NUM_BG, Colors.NUM_PRESSED, Colors.WHITE, Fonts.BTN_M, 'left', 30)
    OPERATOR = get_btn_style.__func__(Colors.OP_BG, Colors.OP_PRESSED, Colors.WHITE, Fonts.BTN_L)
    FUNCTION = get_btn_style.__func__(Colors.FUNC_BG, Colors.FUNC_PRESSED, 'black', Fonts.BTN_S)
    
    OP_ACTIVE = (
        f'QPushButton {{ background-color: {Colors.OP_ACTIVE_BG}; '
        f'color: {Colors.OP_ACTIVE_TEXT}; border-radius: {Dimensions.BTN_RADIUS}px; '
        f'font-size: {Fonts.BTN_L}px; }}'
    )