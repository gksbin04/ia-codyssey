import time
import random

LOG_FILE = 'mission.log'
AVG_LOG_FILE = 'average_mission.log'
INTERVAL = 5
AVG_INTERVAL = 20


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
    
    def __init__(self):
        self.env_values = {key: 0 for key in DummySensor._ENV_METADATA}
        self.ds = DummySensor()
        self.data_history = []

    def get_sensor_data(self):
        new_data = self.ds.set_env()
        self.env_values.update(new_data)
        self.data_history.append(new_data.copy())
        return self.env_values

    @staticmethod
    def get_formatted_json(data_dict, timestamp=None):
        items = []
        if timestamp:
            items.append(f'"timestamp": "{timestamp}"')
        
        for key, value in data_dict.items():
            items.append(f'"{key}": {value}')
            
        return '{ ' + ', '.join(items) + ' }'
    

    def save_log(self, filename, data_dict):
        json_line = self.get_formatted_json(data_dict, time.ctime())
        try:
            with open(filename, 'a') as f:
                f.write(json_line + '\n')
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

def main():
    RunComputer = MissionComputer()

    print('--- Mars Mission Computer Monitor Started ---')
    print(f'Interval: {INTERVAL}s / Avg Interval: {AVG_INTERVAL}s')

    next_run_time = time.time()
    last_avg_time = time.time()

    try:
        while True:
            current_env = RunComputer.get_sensor_data()
            current_time = time.time()
            
            if current_time - last_avg_time >= AVG_INTERVAL:
                avg_data, run_count = RunComputer.calculate_average()
                
                if avg_data:
                    avg_json = RunComputer.get_formatted_json(avg_data)
                    print('\n' + '=' * 45)
                    print(f'[Periodic Average Report - {time.ctime()}, {run_count} samples]')
                    print(avg_json)
                    print('=' * 45)
                    RunComputer.save_log(AVG_LOG_FILE, avg_data)
                
                RunComputer.save_log(LOG_FILE, current_env)
                last_avg_time = current_time
            else:
                json_str = RunComputer.get_formatted_json(current_env)
                print(f'\n[Monitor - {time.ctime()}]')
                print(json_str)
                RunComputer.save_log(LOG_FILE, current_env)

            next_run_time += INTERVAL
            sleep_time = next_run_time - time.time()
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print('\nSystem stopped....')

if __name__ == '__main__':
    main()