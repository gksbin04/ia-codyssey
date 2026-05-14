import random

LOG_FILE = 'mission_log.csv'
TOTAL_MEASUREMENTS = 20

START_DATE = '2026-04-02'
START_TIME = '07:42:30'
TIME_STEP_SEC = 10

ITERATIONS_PER_SEC = 7000000

class MarsClock:
    @staticmethod
    def is_leap_year(year):
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
 
    @staticmethod
    def add_seconds(date_str, time_str, sec):
        y, m, d = map(int, date_str.split('-'))
        hh, mm, ss = map(int, time_str.split(':'))

        ss += sec
        mm += ss // 60
        ss %= 60
        hh += mm // 60
        mm %= 60
        days = hh // 24
        hh %= 24

        for _ in range(days):
            d += 1
            limit = 29 if m == 2 and MarsClock.is_leap_year(y) else \
                    31 if m in (1, 3, 5, 7, 8, 10, 12) else 30
            if d > limit:
                d = 1
                m += 1
                if m > 12:
                    m = 1
                    y += 1

        return f'{y:04d}-{m:02d}-{d:02d}', f'{hh:02d}:{mm:02d}:{ss:02d}'


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
        self._date = START_DATE
        self._time = START_TIME
        self.header_exists = False
        self._env_values = {key: 0 for key in self._ENV_METADATA}

    def set_env(self):
        for key, info in self._ENV_METADATA.items():
            if 'range' in info:
                low, high = info['range']
                self._env_values[key] = round(random.uniform(low, high), 2)

    def get_current_time(self):
        return self._date, self._time

    def get_env(self, time_step=TIME_STEP_SEC):
        self._date, self._time = MarsClock.add_seconds(
            self._date, self._time, time_step
        )
        self._env_values['Date'] = self._date
        self._env_values['Time'] = self._time

        try:
            with open(LOG_FILE, 'r') as f:
                lines = [l for l in f if l.strip()]
                if lines:
                    self.header_exists = True
                    parts = lines[-1].split(', ')
                    if len(parts) >= 2 and parts[0] != 'Date':
                        self._date = parts[0]
                        self._time = parts[1]

        except FileNotFoundError:
            self.header_exists = False
        except (PermissionError, OSError):
            print('로그 파일을 읽을 수 없습니다. 권한을 확인하세요.')
        except Exception as e:
            print(f'예상치 못한 오류 발생: {e}')

        try:
            with open(LOG_FILE, 'a') as f:
                if not self.header_exists:
                    f.write(', '.join(self._ENV_METADATA.keys()) + '\n')
                    self.header_exists = True

                values = [str(self._env_values[k]) for k in self._ENV_METADATA]
                f.write(', '.join(values) + '\n')
        except (PermissionError, OSError) as e:
            print(f'로그 기록 실패: {e}')

        return self._env_values


def main():
    ds = DummySensor()
    print('--- 화성 기지 미션 컴퓨터 가동 ---')
    gt_date, gt_time = ds.get_current_time()
    print(f'기준 시간: {gt_date} {gt_time} ({TIME_STEP_SEC}초 간격 시작)')

    for i in range(TOTAL_MEASUREMENTS):
        for s in range(1, TIME_STEP_SEC + 1):
            print(f'\r... {s}초 동안 데이터 수집 중 ...', end='', flush=True)
            for _ in range(ITERATIONS_PER_SEC):
                pass
        
        ds.set_env()
        data = ds.get_env()

        print(f'\n[{i+1}/{TOTAL_MEASUREMENTS}] {data["Date"]} {data["Time"]}')
        for key, value in data.items():
            if key in ['Date', 'Time']:
                continue
            unit = ds._ENV_METADATA[key]['unit']
            clean_key = key.replace('_', ' ')
            print(f'  - {clean_key}: {value}{unit}')


if __name__ == '__main__':
    main()