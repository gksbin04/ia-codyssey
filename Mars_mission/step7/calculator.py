import sys
from PyQt5.QtWidgets import QApplication
# 파일 이름과 클래스 이름을 정확히 매칭하여 임포트
from CalculatorModel import CalculatorModel
from CalculatorView import CalculatorView
from CalculatorController import CalculatorController

def main():
    app = QApplication(sys.argv)

    # MVC 각 구성 요소 생성
    model = CalculatorModel()
    view = CalculatorView()
    # 컨트롤러에서 모델과 뷰를 연결 (조립)
    controller = CalculatorController(model, view)

    view.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()