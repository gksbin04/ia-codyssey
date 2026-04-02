import random

LOG_FILE = 'mission.log'
TOTAL_MEASUREMENTS = 50

START_DATE = "2026-04-02" 
START_TIME = "02:40:30"
TIME_STEP_SEC = 10


class MarsClock:
    @staticmethod
    def is_leap_year(year):
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    @staticmethod
    def days_in_month(year, month):
        if month == 2:
            return 29 if MarsClock.is_leap_year(year) else 28
        return 31 if month in (1, 3, 5, 7, 8, 10, 12) else 30

    @staticmethod
    def add_seconds(date_str, time_str, seconds_to_add):
        y, m, d = map(int, date_str.split('-'))
        hh, mm, ss = map(int, time_str.split(':'))
        
        ss += seconds_to_add
        mm += ss // 60; ss %= 60
        hh += mm // 60; mm %= 60
        days_to_add = hh // 24; hh %= 24
        
        for _ in range(days_to_add):
            d += 1
            if d > MarsClock.days_in_month(y, m):
                d = 1
                m += 1
                if m > 12:
                    m = 1
                    y += 1
        
        return f"{y:04d}-{m:02d}-{d:02d}", f"{hh:02d}:{mm:02d}:{ss:02d}"
    
class DummySensor:

    _ENV_METADATA = {
        'Date': {'unit': ''},
        'Time': {'unit': ''},
        'mars_base_internal_temperature': {'range': (18, 30), 'unit': '도'},
        'mars_base_external_temperature': {'range': (0, 21), 'unit': '도'},
        'mars_base_internal_humidity': {'range': (50, 60), 'unit': '%'},
        'mars_base_external_illuminance': {'range': (500, 715), 'unit': 'W/m2'},
        'mars_base_internal_co2': {'range': (0.02, 0.1), 'unit': '%'},
        'mars_base_internal_oxygen': {'range': (4, 7), 'unit': '%'}
    }

    def __init__(self):
        self._current_date = START_DATE
        self._current_time = START_TIME
        self.header_exists = False

        try:
            with open(LOG_FILE, 'r') as f:
                first_line = f.readline()
                if first_line:
                    self.header_exists = True

                    last_line = first_line
                    for line in f:
                        if line.strip():
                            last_line = line

                    parts = last_line.strip().split(', ')
                    if len(parts) >= 2 and parts[0] != 'Date':
                        self._current_date = parts[0]
                        self._current_time = parts[1]             
        except FileNotFoundError:
            self.header_exists = False
        except (PermissionError, OSError):
            print("로그 파일을 읽을 수 없습니다. 권한을 확인하세요. 기본 시간으로 시작합니다.")
        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}. 기본 시간으로 시작합니다.")
            
        self._env_values = {key: 0 for key in self._ENV_METADATA}

    def set_env(self):
        for key, info in self._ENV_METADATA.items():
            if 'range' in info:
                low, high = info['range']
                self._env_values[key] = round(random.uniform(low, high), 2)

    def get_env(self, time_step=TIME_STEP_SEC):
        self._current_date, self._current_time = MarsClock.add_seconds(
            self._current_date, self._current_time, time_step
        )
        
        self._env_values['Date'] = self._current_date
        self._env_values['Time'] = self._current_time

        try:
            with open(LOG_FILE, 'a') as f:
                if not self.header_exists:
                    f.write(', '.join(self._ENV_METADATA.keys()) + '\n')
                    self.header_exists = True

                values = [str(self._env_values[key]) for key in self._ENV_METADATA]
                f.write(', '.join(values) + '\n')
        except (PermissionError, OSError) as e:
            print(f"로그 기록 실패: 파일을 다른 프로그램이 사용 중이거나 권한이 없습니다. {e}")

        return self._env_values
    

def main():
    ds = DummySensor()
    print('--- 화성 기지 미션 컴퓨터 가동 ---')
    print(f'기준 시간: {ds._current_date} {ds._current_time} ({TIME_STEP_SEC}초 간격 기록 시작)')

    for i in range(TOTAL_MEASUREMENTS):
        ds.set_env()
        data = ds.get_env(time_step=TIME_STEP_SEC)

        print(f'\n[{i+1}/{TOTAL_MEASUREMENTS}] {data["Date"]} {data["Time"]}')
        for key, value in data.items():
            if key in ['Date', 'Time']: continue
            unit = ds._ENV_METADATA[key]['unit']
            print(f'  - {key.replace("_", " ")}: {value}{unit}')

if __name__ == '__main__':
    main()