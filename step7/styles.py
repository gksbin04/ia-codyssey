class Dimensions:
    WIN_WIDTH = 350
    WIN_HEIGHT = 550
    BTN_RADIUS = 35
    DISPLAY_HEIGHT = 120
    SPACING = 10

class Colors:
    BLACK = 'black'
    WHITE = 'white'
    GRAY_TEXT = '#a0a0a0'
    NUM_BG = '#333333'
    NUM_PRESSED = '#737373'
    OP_BG = '#FF9F0A'
    OP_PRESSED = '#FCC78F'
    OP_ACTIVE_BG = 'white'
    OP_ACTIVE_TEXT = '#FF9F0A'
    FUNC_BG = '#A5A5A5'
    FUNC_PRESSED = '#D9D9D9'

class Fonts:
    DISPLAY = 60
    EXPR = 20
    BTN_L = 32
    BTN_M = 28
    BTN_S = 24

def _get_btn_style(bg, pressed_bg, text_color, font_size, align='center', padding=0):
    return (f'QPushButton {{ background-color: {bg}; color: {text_color}; border-radius: {Dimensions.BTN_RADIUS}px; font-size: {font_size}px; text-align: {align}; padding-left: {padding}px; border: none; }} '
            f'QPushButton:pressed {{ background-color: {pressed_bg}; }}')

class StyleSheets:
    MAIN_WINDOW = f'background-color: {Colors.BLACK};'
    DISPLAY = f'padding: 10px 20px; border: none; background-color: {Colors.BLACK}; color: {Colors.WHITE};'
    EXPR = f'font-size: {Fonts.EXPR}px; padding: 0 20px; border: none; background-color: {Colors.BLACK}; color: {Colors.GRAY_TEXT};'

    NUMBER = _get_btn_style(Colors.NUM_BG, Colors.NUM_PRESSED, Colors.WHITE, Fonts.BTN_M)
    ZERO = _get_btn_style(Colors.NUM_BG, Colors.NUM_PRESSED, Colors.WHITE, Fonts.BTN_M, 'left', 30)
    OPERATOR = _get_btn_style(Colors.OP_BG, Colors.OP_PRESSED, Colors.WHITE, Fonts.BTN_L)
    FUNCTION = _get_btn_style(Colors.FUNC_BG, Colors.FUNC_PRESSED, 'black', Fonts.BTN_S)
    OP_ACTIVE = f'QPushButton {{ background-color: {Colors.OP_ACTIVE_BG}; color: {Colors.OP_ACTIVE_TEXT}; border-radius: {Dimensions.BTN_RADIUS}px; font-size: {Fonts.BTN_L}px; border: none; }}'