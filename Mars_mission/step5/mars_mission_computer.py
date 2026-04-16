import json
import os
import platform
import ctypes
import subprocess
import logging
from logging.handlers import RotatingFileHandler


class Config:
    """미션 컴퓨터의 설정을 관리하는 클래스입니다."""
    LOG_FILE = 'mission.log'
    MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB
    BACKUP_COUNT = 3
    SETTING_FILE = 'setting.txt'

    DISPLAY_NAMES = {
        'os': '운영체계',
        'os_ver': '운영체계 버전',
        'cpu_type': 'CPU의 타입',
        'cores': 'CPU의 코어 수',
        'mem_total': '메모리의 크기',
        'cpu_load': 'CPU 실시간 사용량',
        'mem_load': '메모리 실시간 사용량'
    }


class SystemProvider:
    """운영체제별 시스템 정보를 제공하기 위한 인터페이스 클래스입니다."""
    def get_memory_size(self):
        """총 메모리 크기를 반환합니다."""
        raise NotImplementedError

    def get_cpu_load(self):
        """현재 CPU 사용량을 반환합니다."""
        raise NotImplementedError

    def get_memory_load(self):
        """현재 메모리 사용량을 반환합니다."""
        raise NotImplementedError


class WindowsProvider(SystemProvider):
    """Windows 환경에서 시스템 정보를 수집하는 프로바이더 클래스입니다."""
    def _get_memory_info_windows(self):
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullTotalPhys, stat.dwMemoryLoad

    def get_memory_size(self):
        try:
            total, _ = self._get_memory_info_windows()
            return f'{round(total / (1024 ** 3), 2)}GB'
        except Exception as e:
            logging.error(f'메모리 크기 수집 실패: {e}')
        return '알 수 없음'

    def get_cpu_load(self):
        try:
            output = subprocess.check_output('wmic cpu get loadpercentage', shell=True).decode('utf-8')
            lines = [line.strip() for line in output.split('\n') if line.strip().isdigit()]
            if lines:
                return f'{lines[0]}%'
        except Exception as e:
            logging.error(f'CPU 부하 수집 실패: {e}')
        return '알 수 없음'

    def get_memory_load(self):
        try:
            _, load = self._get_memory_info_windows()
            return f'{load}%'
        except Exception as e:
            logging.error(f'메모리 부하 수집 실패: {e}')
        return '알 수 없음'


class DefaultProvider(SystemProvider):
    """Windows 이외의 환경에서 동작하는 기본 프로바이더 클래스입니다."""
    def get_memory_size(self):
        return '지원하지 않는 운영체제'

    def get_cpu_load(self):
        return '지원하지 않는 운영체제'

    def get_memory_load(self):
        return '지원하지 않는 운영체제'


class SystemInfo:
    """시스템 하드웨어 정보를 수집하는 정적 클래스입니다."""
    
    @classmethod
    def _get_provider(cls):
        """운영체제에 맞는 프로바이더를 반환합니다."""
        if platform.system() == 'Windows':
            return WindowsProvider()
        return DefaultProvider()

    @classmethod
    def get_os(cls):
        return platform.system()

    @classmethod
    def get_os_version(cls):
        return platform.version()

    @classmethod
    def get_cpu_type(cls):
        return platform.processor()

    @classmethod
    def get_cpu_core_count(cls):
        return os.cpu_count()

    @classmethod
    def get_memory_size(cls):
        return cls._get_provider().get_memory_size()

    @classmethod
    def get_cpu_usage(cls):
        return cls._get_provider().get_cpu_load()

    @classmethod
    def get_memory_usage(cls):
        return cls._get_provider().get_memory_load()


class MissionComputer:
    """화성 미션 컴퓨터의 환경 모니터링 및 시스템 정보를 관리하는 메인 클래스입니다."""
    def __init__(self):
        self._setup_logger()

    def _setup_logger(self):
        """logging 모듈을 초기화하고 RotatingFileHandler를 설정합니다."""
        self.logger = logging.getLogger('MissionComputerLogger')
        self.logger.setLevel(logging.INFO)
        
        # 이미 핸들러가 있다면 추가하지 않음
        if not self.logger.handlers:
            handler = RotatingFileHandler(
                Config.LOG_FILE, 
                maxBytes=Config.MAX_LOG_SIZE, 
                backupCount=Config.BACKUP_COUNT, 
                encoding='utf-8'
            )
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def record_data(self, data_dict):
        """수집된 데이터를 로거를 통해 파일에 기록합니다."""
        single_line_json = json.dumps(data_dict, ensure_ascii=False)
        self.logger.info(single_line_json)

    def display_data(self, data_dict):
        """수집된 데이터를 터미널에 JSON 형태로 출력합니다."""
        print(json.dumps(data_dict, ensure_ascii=False, indent=4))

    def generate_cpu_load(self):
        """CPU 실시간 사용량을 확인할 수 있도록 임의의 부하를 발생시킵니다."""
        try:
            print("CPU 부하 발생 중... (중지하려면 Ctrl+C)")
            while True:
                # 아래 줄을 주석 처리/해제하여 부하 발생 여부를 쉽게 제어할 수 있습니다.
                _ = [x**2 for x in range(10000)] 
                # time.sleep(0.1) # 부하를 약간 줄이려면 이 주석을 해제하세요.
        except KeyboardInterrupt:
            print('\n부하 발생 중지....')

    def get_setting_keys(self):
        try:
            with open(Config.SETTING_FILE, 'r', encoding='utf-8') as f:
                # 수동 파싱 대신 표준 라이브러리 활용
                import json
                settings = json.load(f)
            return [k for k, v in settings.items() if v]
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _collect_info_data(self):
        """시스템 하드웨어 정보 데이터를 순수하게 수집하여 딕셔너리로 반환합니다."""
        info = {}
        try:
            info[Config.DISPLAY_NAMES['os']] = SystemInfo.get_os()
            info[Config.DISPLAY_NAMES['os_ver']] = SystemInfo.get_os_version()
            info[Config.DISPLAY_NAMES['cpu_type']] = SystemInfo.get_cpu_type()
            info[Config.DISPLAY_NAMES['cores']] = SystemInfo.get_cpu_core_count()
            info[Config.DISPLAY_NAMES['mem_total']] = SystemInfo.get_memory_size()
        except Exception as e:
            info['error'] = f'시스템 정보 수집 실패: {e}'
        return info

    def get_mission_computer_info(self):
        """수집된 시스템 정보를 필터링 후 화면에 출력하고 로그에 기록합니다."""
        info = self._collect_info_data()

        settings = self.get_setting_keys()
        if settings is not None:
            filtered_info = {k: v for k, v in info.items() if k in settings or k == 'error'}
        else:
            filtered_info = info

        self.display_data(filtered_info)
        self.record_data(filtered_info)
        return filtered_info

    def _collect_load_data(self):
        """시스템 부하 정보 데이터를 순수하게 수집하여 딕셔너리로 반환합니다."""
        load_info = {}
        try:
            load_info['CPU 실시간 사용량'] = getattr(SystemInfo, 'get_cpu_usage')()
            load_info['메모리 실시간 사용량'] = getattr(SystemInfo, 'get_memory_usage')()
        except Exception as e:
            load_info['error'] = f'시스템 부하 정보를 가져오는데 실패했습니다: {e}'
        return load_info

    def get_mission_computer_load(self):
        """수집된 시스템 부하 정보를 필터링 후 화면에 출력하고 로그에 기록합니다."""
        load_info = self._collect_load_data()

        settings = self.get_setting_keys()
        if settings is not None:
            filtered_load = {k: v for k, v in load_info.items() if k in settings or k == 'error'}
        else:
            filtered_load = load_info

        self.display_data(filtered_load)
        self.record_data(filtered_load)
        return filtered_load


def main():
    runComputer = MissionComputer()

    runComputer.get_mission_computer_info()
    runComputer.get_mission_computer_load()
    # CPU 부하를 발생시키려면 아래 주석을 해제하세요.
    runComputer.generate_cpu_load()


if __name__ == '__main__':
    main()
