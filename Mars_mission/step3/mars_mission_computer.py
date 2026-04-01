import random

LOG_FILE = 'mission.log'
TOTAL_MEASUREMENTS = 3

START_HOUR = 2
START_MIN = 40
START_SEC = 30


class DummySensor:

    _ENV_METADATA = {
        'Time_Stamp': {'unit': ''},
        'mars_base_internal_temperature': {'range': (18, 30), 'unit': '도'},
        'mars_base_external_temperature': {'range': (0, 21), 'unit': '도'},
        'mars_base_internal_humidity': {'range': (50, 60), 'unit': '%'},
        'mars_base_external_illuminance': {'range': (500, 715), 'unit': 'W/m2'},
        'mars_base_internal_co2': {'range': (0.02, 0.1), 'unit': '%'},
        'mars_base_internal_oxygen': {'range': (4, 7), 'unit': '%'}
    }

    def __init__(self):

        try:
            with open(LOG_FILE, 'r') as f:
                self.header_exists = f.readline() != ''
        except FileNotFoundError:
            self.header_exists = False

        self._mission_count = 0

        self._start_total_seconds = (START_HOUR * 3600) + (START_MIN * 60) + START_SEC
        self._env_values = {key: 0 for key in self._ENV_METADATA}

    def set_env(self):
        for key, info in self._ENV_METADATA.items():
            if key == 'Time_Stamp': continue

            low, high = info['range']
            self._env_values[key] = round(random.uniform(low, high), 2)

    def get_env(self):
        self._mission_count += 1
        current_total_seconds = self._start_total_seconds + (self._mission_count * 10)

        h = (current_total_seconds // 3600) % 24
        m = (current_total_seconds % 3600) // 60
        s = current_total_seconds % 60
        time_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

        self._env_values['Time_Stamp'] = time_str

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

    for i in range(TOTAL_MEASUREMENTS):
        ds.set_env()
        data = ds.get_env()

        print(f'\n[{i+1}/{TOTAL_MEASUREMENTS}] 측정 완료 시각: {data["Time_Stamp"]}')

        for key, value in data.items():
            if key == 'Time_Stamp': continue
            unit = ds._ENV_METADATA[key]['unit']
            print(f'  - {key}: {value}{unit}')

if __name__ == '__main__':
    main()