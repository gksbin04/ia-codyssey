import random

LOG_FILE = 'mission.log'
TOTAL_MEASUREMENTS = 50

START_DATE = "2026-04-02" 
START_TIME = "02:40:30"

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
        """날짜와 시간에 초를 더해 새로운 타임스탬프 반환"""
        y, m, d = map(int, date_str.split('-'))
        hh, mm, ss = map(int, time_str.split(':'))
        
        ss += seconds_to_add
        
        # 초 -> 분 -> 시 -> 일 올림 계산
        mm += ss // 60; ss %= 60
        hh += mm // 60; mm %= 60
        days_to_add = hh // 24; hh %= 24
        
        # 일 -> 월 -> 년 올림 계산
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
                lines = f.readlines()
                # 헤더 외에 데이터가 있다면 마지막 줄에서 날짜와 시간 추출
                if len(lines) > 1:
                    last_line = lines[-1].split(', ')
                    self._current_date = last_line[0]
                    self._current_time = last_line[1]
                    self.header_exists = True
        except FileNotFoundError:
            self.header_exists = False

        self._env_values = {key: 0 for key in self._ENV_METADATA}

    def set_env(self):
        for key, info in self._ENV_METADATA.items():
            if 'range' in info:
                low, high = info['range']
                self._env_values[key] = round(random.uniform(low, high), 2)

    def get_env(self, time_step=10):
        self._current_date, self._current_time = MarsClock.add_seconds(
            self._current_date, self._current_time, time_step
        )
        
        self._env_values['Date'] = self._current_date
        self._env_values['Time'] = self._current_time

        with open(LOG_FILE, 'a') as f:
            if not self.header_exists:
                header = ', '.join(self._ENV_METADATA.keys()) + '\n'
                f.write(header)
                self.header_exists = True

            values = [str(self._env_values[key]) for key in self._ENV_METADATA]
            log_line = ', '.join(values) + '\n'
            f.write(log_line)

        return self._env_values
    

def main():
    ds = DummySensor()
    print('--- 화성 기지 미션 컴퓨터 가동 ---')

    prev_temp = 0

    for i in range(TOTAL_MEASUREMENTS):
        ds.set_env()
        current_temp = ds._env_values['mars_base_external_temperature']
        step = 1 if abs(current_temp - prev_temp) > 5 else 10
        prev_temp = current_temp
        
        data = ds.get_env(time_step=step)

        print(f'[{i+1}] {data["Date"]} {data["Time"]} (주기: {step}s)')

        for key, value in data.items():
            if key in ['Date', 'Time']:
                continue
                
            unit = ds._ENV_METADATA[key]['unit']
            clean_key = key.replace('_', ' ')
            print(f'  - {clean_key}: {value}{unit}')
        
if __name__ == '__main__':
    main()