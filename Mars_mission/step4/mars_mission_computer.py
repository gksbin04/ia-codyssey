import time
import random

LOG_FILE = 'mission.log'
AVG_LOG_FILE = 'average_mission.log'
INTERVAL = 5
AVG_INTERVAL = 20
SAMPLES_NEEDED = AVG_INTERVAL // INTERVAL


class DummySensor:
    _ENV_METADATA = {
        'mars_base_internal_temperature': (18, 30),
        'mars_base_external_temperature': (0, 21),
        'mars_base_internal_humidity': (50, 60),
        'mars_base_external_illuminance': (500, 715),
        'mars_base_internal_co2': (0.02, 0.1),
        'mars_base_internal_oxygen': (4, 7)
    }

    def __init__(self):
        self._env_values = {key: 0 for key in self._ENV_METADATA}

    def set_env(self):
        for key, value_range in self._ENV_METADATA.items():
            low, high = value_range
            self._env_values[key] = round(random.uniform(low, high), 2)
        
        return self._env_values
    
    def get_env(self):
        return self._env_values


class MissionComputer:
    def __init__(self, sensor):
        self.ds = sensor
        self.env_values = {key: 0.0 for key in DummySensor._ENV_METADATA}
        self.data_history = []

    @staticmethod
    def get_formatted_json(data_dict, timestamp=None):
        lines = ['{']
        if timestamp:
            lines.append(f'    "timestamp": "{timestamp}",')
        
        items = list(data_dict.items())
        for i, (key, value) in enumerate(items):
            comma = ',' if i < len(items) - 1 else ''
            lines.append(f'    "{key}": {value}{comma}')
            
        lines.append('}')
        return '\n'.join(lines)

    def save_log(self, filename, data_dict):
        json_line = self.get_formatted_json(data_dict, time.ctime())
        try:
            single_line = json_line.replace('\n', '').replace('    ', '')
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(single_line + '\n')
        except OSError as e:
            print(f'로그 저장 실패 ({filename}): {e}')

    def calculate_average(self):
        if not self.data_history:
            return None, 0
        
        averages = {}
        keys = self.env_values.keys()
        count = len(self.data_history)
        
        for key in keys:
            total = sum(data[key] for data in self.data_history)
            averages[key] = round(total / count, 2)
            
        self.data_history = []
        return averages, count

    def get_sensor_data(self):
        print('--- Mars Mission Computer Monitor Started ---')
        print(f'Interval: {INTERVAL}s / Avg Interval: {AVG_INTERVAL}s')

        next_run_time = time.time()

        try:
            while True:

                new_data = self.ds.set_env()
                self.env_values.update(new_data)
                self.data_history.append(new_data.copy())

                print('\n' + '=' * 50)
                print(f'\n[Monitor - {time.ctime()}]')
                print(self.get_formatted_json(self.env_values))
                self.save_log(LOG_FILE, self.env_values)

                if len(self.data_history) >= SAMPLES_NEEDED:
                    avg_data, run_count = self.calculate_average()
                    if avg_data:
                        print(f'[Periodic Average Report - {time.ctime()}, {run_count} samples]')
                        print(self.get_formatted_json(avg_data))
                        self.save_log(AVG_LOG_FILE, avg_data)

                next_run_time += INTERVAL
                sleep_time = next_run_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print('\nSystem stopped....')


def main():
    sensor = DummySensor()

    RunComputer = MissionComputer(sensor)

    RunComputer.get_sensor_data()


if __name__ == '__main__':
    main()