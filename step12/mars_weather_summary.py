import csv
import sys
import struct
import zlib
from datetime import datetime, timedelta
import os
import importlib.util
import getpass

try:
    import mysql.connector
except ImportError:
    print('MySQL 연결을 위해 mysql-connector-python 패키지가 필요합니다.')
    sys.exit(1)  # 패키지가 없으면 에러 메시지를 내고 즉시 프로그램을 종료합니다.


DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'mars_db'
}

def resolve_db_config():
    """
    Configuration as Code 방식과 런타임 패스워드 입력을 결합하여
    가장 안전하고 유연하게 데이터베이스 설정을 구성합니다.
    """
    config = dict(DB_CONFIG)
    local_filename = 'db_config.local.py'
    
    # 현재 스크립트가 위치한 디렉토리 경로를 동적으로 가져옴
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(script_dir, local_filename)
    
    # 1. 로컬 설정 파이썬 파일(.py)이 존재하면 모듈로 로드하여 설정 병합
    if os.path.isfile(local_path):
        spec = importlib.util.spec_from_file_location('db_config_local', local_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'DB_CONFIG'):
            config.update(module.DB_CONFIG)
        if hasattr(module, 'MYSQL_PASSWORD'):
            config['password'] = module.MYSQL_PASSWORD

    # 2. 시스템 환경 변수가 설정되어 있다면 최우선 적용
    env_password = os.environ.get('MYSQL_PASSWORD')
    if env_password is not None:
        config['password'] = env_password

    # 3. 비밀번호가 어디에도 없다면 화면 보호(getpass)와 함께 직접 물어보기 (Fallback)
    if not config.get('password'):
        prompt = f"MySQL 비밀번호 ({config.get('user', 'root')}): "
        config['password'] = getpass.getpass(prompt)

    return config


class MySQLHelper:
    """
    MySQL 데이터베이스 연결, 해제 및 쿼리 실행을 전담하는 도우미 클래스입니다.
    """
    
    def __init__(self, host='localhost', user='root', password='', database='mars_db'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """with 구문 진입 시 자동으로 연결합니다."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 구문 종료 시 예외 발생 여부와 상관없이 안전하게 닫습니다."""
        self.close()

    def connect(self):
        """MySQL 데이터베이스에 안전하게 연결합니다."""
        try:
            config = {
                'host': self.host,
                'user': self.user,
                'password': self.password,
                'database': self.database
            }
            self.conn = mysql.connector.connect(**config)
            self.cursor = self.conn.cursor()
            print('MySQL 데이터베이스 연결에 성공했습니다.')
        except Exception as e:
            print(f'데이터베이스 연결 중 오류가 발생했습니다: {e}')

    def execute_query(self, query, params = None):
        """단일 쿼리를 실행합니다."""
        if not self.conn or not self.cursor:
            print('데이터베이스가 연결되어 있지 않습니다.')
            return
            
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            print(f'쿼리 실행 중 오류가 발생했습니다: {e}')

    def fetch_all(self, query, params = None):
        """SELECT 쿼리를 실행하고 조회된 모든 결과(튜플 리스트)를 반환합니다."""
        if not self.conn or not self.cursor:
            print('데이터베이스가 연결되어 있지 않습니다.')
            return []
            
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f'데이터 조회 중 오류가 발생했습니다: {e}')
            return []

    def close(self):
        """데이터베이스 연결을 안전하게 종료합니다."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print('데이터베이스 연결을 안전하게 종료했습니다.')
        except Exception as e:
            print(f'데이터베이스 종료 중 오류가 발생했습니다: {e}')


class MarsWeatherPipeline:
    """
    데이터베이스 적재부터 분석, 시각화까지 전체 흐름을 제어하는 파이프라인 클래스입니다.
    """
    
    def __init__(self, config):
        self.db_helper = MySQLHelper(
            host=config.get('host', 'localhost'),
            user=config.get('user', 'root'),
            password=config.get('password', ''),
            database=config.get('database', 'mars_db')
        )

    def process(self, csv_filepath):
        """전체 데이터 파이프라인을 순차적으로 실행합니다."""
        self.db_helper.connect()
        
        # DB 연결 실패 시 후속 작업 중단 (Fail-Fast)
        if not self.db_helper.conn:
            print("데이터베이스 연결 실패로 파이프라인을 중단합니다.")
            return
            
        self._setup_database()
        self.migrate_weather_data(csv_filepath)
        
        rows = self._fetch_weather_data()
        if rows:
            WeatherAnalyzer.print_summary(rows)
            WeatherVisualizer.save_summary_png(rows)
            
        self.db_helper.close()

    def _setup_database(self):
        """분석에 필요한 mars_weather 테이블의 스키마를 정의하고 생성합니다."""
        
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS mars_weather (
                weather_id INT AUTO_INCREMENT PRIMARY KEY,
                mars_date DATETIME NOT NULL,
                temp INT NOT NULL,
                storm INT NOT NULL
            )
        '''
        self.db_helper.execute_query(create_table_query)

    def migrate_weather_data(self, csv_filepath):
        """
        CSV 파일을 읽어들여 데이터를 보정한 후, 데이터베이스에 적재합니다.
        
        과제 제약 조건에 따라, 플레이스홀더(%s) 대신 온전한 쿼리 문자열을 조립해 반복 실행합니다.
        """
        try:
            # 과제 요구사항: utf-8-sig로 BOM 문자를 처리합니다.
            with open(csv_filepath, 'r', encoding = 'utf-8-sig') as file:
                reader = csv.reader(file)
                header = next(reader, None)
                
                # 과제 요구사항: CSV 읽기 및 내용 확인 출력
                if header:
                    print(f"CSV 헤더: {','.join(header)}")

                # 헤더의 오타(stom)를 감지하여 동적으로 인덱스 매핑
                date_idx = header.index('mars_date') if 'mars_date' in header else 1
                temp_idx = header.index('temp') if 'temp' in header else 2
                
                storm_idx = header.index('storm') if 'storm' in header else (header.index('stom') if 'stom' in header else 3)
                
                # 기존 데이터를 싹 지우고 AUTO_INCREMENT 카운터를 1로 초기화합니다.
                self.db_helper.execute_query('TRUNCATE TABLE mars_weather')
                
                for row in reader:
                    # 내용 확인 출력
                    print(','.join(row))
                    
                    if len(row) >= 4:
                        try:
                            temp_val = int(round(float(row[temp_idx])))
                            storm_val = int(row[storm_idx])
                            
                            # 과제 요구사항: 온전한 INSERT 쿼리 문자열로 변환 후 출력 및 반복 실행
                            insert_query = f"INSERT INTO mars_weather (mars_date, temp, storm) VALUES ('{row[date_idx]}', {temp_val}, {storm_val});"
                            print(f"실행 쿼리: {insert_query}")
                            self.db_helper.execute_query(insert_query)
                        except ValueError as e:
                            print(f'데이터 변환 중 오류가 발생했습니다: {e}')
                
                print('CSV 데이터 마이그레이션이 완료되었습니다.')
        except FileNotFoundError:
            print(f'파일을 찾을 수 없습니다: {csv_filepath}')
        except Exception as e:
            print(f'데이터 마이그레이션 중 오류가 발생했습니다: {e}')

    def _fetch_weather_data(self):
        """데이터베이스에서 분석할 전체 날씨 데이터를 날짜순으로 조회합니다."""
        select_query = 'SELECT mars_date, temp, storm FROM mars_weather ORDER BY mars_date ASC'
        return self.db_helper.fetch_all(select_query)


class WeatherAnalyzer:
    """조회된 날씨 데이터를 기반으로 통계를 내고 요약 보고서를 터미널에 출력하는 클래스입니다."""
    
    @staticmethod
    def print_summary(rows):
        """
        날씨 등급별 발생 일수를 통계 내고 이동 예정일의 안전성을 예측하여 보고서 형태로 출력합니다.
        """
        if not rows:
            print('분석할 날씨 데이터가 데이터베이스에 존재하지 않습니다.')
            return
        
        total_records = len(rows)
        total_temp = sum(row[1] for row in rows)
        avg_temp = total_temp / total_records
        
        # 폭풍 강도에 따른 등급별 일수 계산 초기화
        clear_days = 0         # 1단계: 안전/맑음 (0)
        mild_storm_days = 0    # 2단계: 미세 폭풍 (1 ~ 30) -> 이동 가능!
        strong_storm_days = 0  # 3단계: 강한 폭풍 (31 ~ 70)
        danger_days = 0        # 4단계: 극심한 폭풍 (71 ~ 100) -> 외출 금지
        
        for row in rows:
            storm_val = row[2]
            if storm_val == 0:
                clear_days += 1
            elif storm_val <= 30:
                mild_storm_days += 1
            elif storm_val <= 70:
                strong_storm_days += 1
            else:
                danger_days += 1
        
        # 마지막 기록 날짜 + 1일을 계산하여 이동 예정일 도출
        last_record = rows[-1]
        last_date = last_record[0]
        last_storm_val = last_record[2]
        
        if isinstance(last_date, str):
            # 시간 데이터 포함 여부에 따라 유연하게 파싱
            try:
                last_date = datetime.strptime(last_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                last_date = datetime.strptime(last_date, '%Y-%m-%d')
            
        travel_date = last_date + timedelta(days = 1)
        travel_date_str = travel_date.strftime('%Y-%m-%d')
        
        # [주기 분석 알고리즘] 최근 10일(현재 주기)과 이전 10일(과거 주기)의 폭풍 평균 비교
        current_cycle = rows[-10:] if len(rows) >= 10 else rows
        past_cycle = rows[-20:-10] if len(rows) >= 20 else rows
        
        current_avg_storm = sum(r[2] for r in current_cycle) / len(current_cycle)
        past_avg_storm = sum(r[2] for r in past_cycle) / (len(past_cycle) or 1)
        
        # 현재 주기가 과거 주기보다 잦아들었거나 평균 강도가 40 미만이면 '안전 주기(휴지기)'로 판단
        is_safe_cycle = current_avg_storm <= past_avg_storm or current_avg_storm < 40
        
        # 주기 판단과 전날 폭풍 강도를 결합한 종합 예측 로직
        if is_safe_cycle and last_storm_val == 0:
            storm_status = '「안전 (폭풍 휴지기 진입 및 전날 폭풍 없음. 이동 최적기!)」'
        elif is_safe_cycle and last_storm_val <= 30:
            storm_status = '「이동 가능 (폭풍이 잦아드는 안전 주기에 진입했고, 전날 폭풍도 미미하여 이동 가능한 수준임)」'
        elif not is_safe_cycle and last_storm_val <= 30:
            storm_status = '「주의 (전날 폭풍은 미미하나, 아직 폭풍 발생 주기에 있으므로 이동 시 예의 주시 필요)」'
        elif last_storm_val <= 70:
            storm_status = '「경고 (강한 폭풍 발생 및 불안정 주기. 이동 시 장비 마모 우려)」'
        else:
            storm_status = '「위험/외출 금지 (극심한 모래 폭풍 발생. 기지 내 대기 요망)」'
        
        print('\n==================================================')
        print('             화성 기지 날씨 요약 보고서             ')
        print('==================================================')
        print(f'총 분석 기록 수: {total_records}건')
        print(f'화성 평균 기온: {avg_temp:.2f}도')
        print('--------------------------------------------------')
        print('               [ 상세 폭풍 등급 분류 ]              ')
        print(f'- 맑음/안전 일수 (0)         : {clear_days}일')
        print(f'- 미세 폭풍 일수 (1 ~ 30)    : {mild_storm_days}일 (※ 이동 가능)')
        print(f'- 강한 폭풍 일수 (31 ~ 70)   : {strong_storm_days}일')
        print(f'- 극심한 폭풍 일수 (71 ~ 100): {danger_days}일 (※ 외출 금지)')
        print(f'▶ 총 활동 가능 일수(맑음+미세): {clear_days + mild_storm_days}일 / {total_records}일')
        print('--------------------------------------------------')
        print(f'한송희 박사 이동 예정일: {travel_date_str}')
        print(f'▶ 최근 폭풍 주기 추세: {"안정화 추세 (휴지기)" if is_safe_cycle else "불안정 추세 (위험기)"}')
        print(f'▶ 전날(마지막 기록) 폭풍 강도: {last_storm_val}')
        print(f'이동일 폭풍 예측 결과: {storm_status}')
        print('==================================================')


class WeatherVisualizer:
    """외부 라이브러리 없이 픽셀 단위로 직접 PNG 이미지를 렌더링하는 시각화 클래스입니다."""
    
    @staticmethod
    def save_summary_png(rows):
        """원본 데이터를 1:1로 매핑하여 데이터 유실 없이 온도와 폭풍 그래프를 분리 생성합니다."""
        WeatherVisualizer._create_png(rows, 'TEMP', 'mars_temp_summary.png')
        WeatherVisualizer._create_png(rows, 'STORM', 'mars_storm_summary.png')
        print('결과 그래프가 각각 분리되어 저장되었습니다.')
        print('-> 📈 [온도 그래프] mars_temp_summary.png (동적 스케일링, DDA 연속선, 100일 눈금)')
        print('-> 🚨 [폭풍 그래프] mars_storm_summary.png (데이터 유실 없는 원본 1:1 매핑 막대그래프)')

    @staticmethod
    def _create_png(rows, mode, filename):
        """
        외부 라이브러리 없이 픽셀 단위로 직접 PNG 이미지를 렌더링하는 함수입니다.
        
        Args:
            rows (list): 조회된 데이터 목록 [(mars_date, temp, storm), ...]
            mode (str): 'TEMP' (온도 선 그래프) 또는 'STORM' (폭풍 막대 그래프)
            filename (str): 저장할 대상 PNG 파일 이름
        """
        width, height = 1200, 600
        margin_top, margin_bottom = 80, 60
        margin_left, margin_right = 80, 80
        graph_width = width - margin_left - margin_right
        graph_height = height - margin_top - margin_bottom
        
        # 1. 원본 데이터 유지 (압축 없이 1일 = 1픽셀 매핑하여 데이터 신뢰성 100% 보장)
        compressed = [(record[1], record[2]) for record in rows]

        # 동적 스케일링을 위한 데이터 최대값 도출 (상단 보기 편하도록 20 마진 추가)
        max_temp_val = max(100, max(data[0] for data in compressed))
        max_storm_val = max(100, max(data[1] for data in compressed)) + 20

        # 2. 픽셀 데이터 초기화 (흰색 배경)
        pixels = [[[255, 255, 255] for _ in range(width)] for _ in range(height)]
        
        # 3. Y축 가로 보조선 (4등분 점선)
        for i in range(5):
            ratio = i / 4
            y = (height - margin_bottom) - int(ratio * graph_height)
            for x in range(margin_left, width - margin_right):
                if x % 6 < 3:  # 점선 패턴
                    pixels[y][x] = [230, 230, 230]

        # 4. 글자를 쓰기 위한 초소형 3x5 픽셀 폰트 (알파벳 + 숫자 + 'D')
        font = {
            'T': [1,1,1, 0,1,0, 0,1,0, 0,1,0, 0,1,0], 'E': [1,1,1, 1,0,0, 1,1,0, 1,0,0, 1,1,1],
            'M': [1,0,1, 1,1,1, 1,0,1, 1,0,1, 1,0,1], 'P': [1,1,0, 1,0,1, 1,1,0, 1,0,0, 1,0,0],
            'S': [0,1,1, 1,0,0, 0,1,0, 0,0,1, 1,1,0], 'O': [0,1,0, 1,0,1, 1,0,1, 1,0,1, 0,1,0],
            'R': [1,1,0, 1,0,1, 1,1,0, 1,0,1, 1,0,1], 'D': [1,1,0, 1,0,1, 1,0,1, 1,0,1, 1,1,0],
            ' ': [0]*15,
            '0': [1,1,1, 1,0,1, 1,0,1, 1,0,1, 1,1,1], '1': [0,1,0, 1,1,0, 0,1,0, 0,1,0, 1,1,1],
            '2': [1,1,1, 0,0,1, 1,1,1, 1,0,0, 1,1,1], '3': [1,1,1, 0,0,1, 1,1,1, 0,0,1, 1,1,1],
            '4': [1,0,1, 1,0,1, 1,1,1, 0,0,1, 0,0,1], '5': [1,1,1, 1,0,0, 1,1,1, 0,0,1, 1,1,1],
            '6': [1,1,1, 1,0,0, 1,1,1, 1,0,1, 1,1,1], '7': [1,1,1, 0,0,1, 0,1,0, 0,1,0, 0,1,0],
            '8': [1,1,1, 1,0,1, 1,1,1, 1,0,1, 1,1,1], '9': [1,1,1, 1,0,1, 1,1,1, 0,0,1, 1,1,1],
            '-': [0,0,0, 0,0,0, 1,1,1, 0,0,0, 0,0,0]
        }
        
        def draw_text(text, start_x, start_y, color, scale=3):
            curr_x = start_x
            for char in text:
                char_data = font.get(char, font[' '])
                for r in range(5):
                    for c in range(3):
                        if char_data[r * 3 + c]:
                            for dy in range(scale):
                                for dx in range(scale):
                                    py = start_y + r*scale + dy
                                    px = curr_x + c*scale + dx
                                    if 0 <= py < height and 0 <= px < width:
                                        pixels[py][px] = color
                curr_x += 4 * scale
                
        # 5. 날짜 세로 기록선 (100일 단위)
        total_days = len(rows)
        for day in range(0, total_days + 1, 100):
            x = margin_left + int((day / total_days) * graph_width)
            if x >= width - margin_right: x = width - margin_right - 1
            for y in range(margin_top, height - margin_bottom):
                if y % 6 < 3: pixels[y][x] = [200, 200, 200]
            # 하단에 D(Day) 라벨 출력 (예: 100D)
            draw_text(f"{day}D", x - 15, height - margin_bottom + 15, [0, 0, 0], scale=2)

        # 6. 모드별(TEMP/STORM) 데이터 시각화
        if mode == 'TEMP':
            # 데이터에 맞춘 동적 온도 스케일링
            prev_x, prev_y = None, None
            for i, data in enumerate(compressed):
                average_temp = data[0]
                
                # 동적으로 구해진 max_temp_val 기준 비율
                average_temp = max(0, min(average_temp, max_temp_val))
                temp_ratio = average_temp / float(max_temp_val)
                
                # 점 위치 계산
                center_x = margin_left + int(((i + 0.5) / len(compressed)) * graph_width)
                temp_y = (height - margin_bottom) - int(temp_ratio * graph_height)
                
                # 현재 점 먼저 찍기
                if margin_top <= temp_y < height - margin_bottom:
                    pixels[temp_y][center_x] = [0, 0, 255]
                    if temp_y + 1 < height - margin_bottom: pixels[temp_y+1][center_x] = [0, 0, 255]

                # 이전 점에서 현재 점까지 빈틈없이 선 그리기 (DDA 알고리즘 적용)
                if prev_x is not None and prev_y is not None:
                    dx_line = center_x - prev_x
                    dy_line = temp_y - prev_y
                    steps = max(abs(dx_line), abs(dy_line))
                    if steps > 0:
                        for s in range(steps + 1):
                            curr_x = prev_x + int(dx_line * (s / steps))
                            curr_y = prev_y + int(dy_line * (s / steps))
                            if margin_top <= curr_y < height - margin_bottom:
                                pixels[curr_y][curr_x] = [0, 0, 255]
                                if curr_y + 1 < height - margin_bottom: pixels[curr_y+1][curr_x] = [0, 0, 255]
                
                prev_x, prev_y = center_x, temp_y

            # TEMP 범례 및 Y축 동적 눈금
            draw_text("TEMP", margin_left, 30, [0, 0, 255], scale=4)
            for i in range(5):
                val = int((i / 4.0) * max_temp_val)
                y = (height - margin_bottom) - int((i / 4) * graph_height) - 5
                draw_text(str(val).rjust(3), 20, y, [0, 0, 0], scale=3)

        elif mode == 'STORM':
            for i, data in enumerate(compressed):
                average_storm = data[1]
                if average_storm > 0:
                    if average_storm <= 30: storm_color = [255, 215, 0]
                    elif average_storm <= 70: storm_color = [255, 140, 0]
                    else: storm_color = [255, 0, 0]
                    
                    storm_bar_height = int((average_storm / float(max_storm_val)) * graph_height)
                    start_y = height - margin_bottom - storm_bar_height
                    
                    x_start = margin_left + int((i / len(compressed)) * graph_width)
                    x_end = margin_left + int(((i + 1) / len(compressed)) * graph_width)
                    
                    # 데이터가 1000개일 때는 간격을 두면 막대가 안 그려질 수 있으므로 최소 1픽셀 보장
                    if x_end <= x_start:
                        x_end = x_start + 1
                        
                    for x in range(x_start, x_end):
                        for y in range(start_y, height - margin_bottom):
                            pixels[y][x] = storm_color

            # STORM 범례 및 동적 Y축 눈금
            mid_val = max_storm_val // 2
            draw_text("STORM", margin_left, 30, [255, 0, 0], scale=4)
            draw_text(str(max_storm_val).rjust(3), 20, margin_top - 5, [255, 0, 0], scale=3)
            draw_text(str(mid_val).rjust(3), 20, margin_top + graph_height // 2 - 5, [255, 0, 0], scale=3)
            draw_text("  0", 20, height - margin_bottom - 5, [255, 0, 0], scale=3)
            
            # 상단 우측 범례 색상표 추가
            for dy in range(20):
                for dx in range(40):
                    if dx < 13: legend_color = [255, 215, 0]
                    elif dx < 26: legend_color = [255, 140, 0]
                    else: legend_color = [255, 0, 0]
                    pixels[30 + dy][margin_left + 160 + dx] = legend_color

        # 7. 그래프 양쪽 테두리 및 축 뚜렷하게 그리기
        for x in range(margin_left, width - margin_right):
            pixels[height - margin_bottom][x] = [0, 0, 0] # 하단 X축
            pixels[margin_top][x] = [0, 0, 0]             # 상단 테두리
        for y in range(margin_top, height - margin_bottom + 1):
            pixels[y][margin_left] = [0, 0, 0]            # 좌측 Y축
            pixels[y][width - margin_right] = [0, 0, 0]   # 우측 테두리

        # 8. 이미지 데이터 1차원 바이트 배열로 변환 및 저장
        img_data = bytearray()
        for row in pixels:
            img_data.append(0)
            for color in row:
                img_data.extend(color)
                
        compressed = zlib.compress(img_data)
        
        def make_chunk(chunk_type, data):
            chunk = struct.pack('>I', len(data)) + chunk_type + data
            crc = zlib.crc32(chunk_type + data) & 0xffffffff
            return chunk + struct.pack('>I', crc)
            
        png_magic = b'\x89PNG\r\n\x1a\n'
        ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        
        with open(filename, 'wb') as f:
            f.write(png_magic + make_chunk(b'IHDR', ihdr) + make_chunk(b'IDAT', compressed) + make_chunk(b'IEND', b''))


def main():
    config = resolve_db_config()
    pipeline = MarsWeatherPipeline(config)
    pipeline.process('mars_weathers_data.csv')


if __name__ == '__main__':
    main()