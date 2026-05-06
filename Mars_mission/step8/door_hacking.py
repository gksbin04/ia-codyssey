from __future__ import annotations

import zipfile
import time
import multiprocessing
import os
import argparse
import struct
import json
from pathlib import Path
import string
from dataclasses import dataclass
from typing import Any
import zlib

# 스크립트 실행 위치와 상관없이 항상 동일한 경로(현재 파일 기준)를 참조하도록 절대 경로를 설정합니다.
BASE_DIR = Path(__file__).resolve().parent
ZIP_FILE_PATH = str(BASE_DIR / 'emergency_storage_key.zip')
PASSWORD_FILE_PATH = str(BASE_DIR / 'password.txt')
CHECKPOINT_FILE_PATH = str(BASE_DIR / 'checkpoint.json')
# 무차별 대입에 사용할 문자셋(숫자 0~9, 영소문자 a~z)과 비밀번호의 길이를 정의합니다.
CHARSET = string.digits + string.ascii_lowercase
PASSWORD_LENGTH = 6
BASE = len(CHARSET) # 36진법(숫자 10개 + 알파벳 26개) 계산을 위한 진법의 밑(Base) 값입니다.

# ── 1. 데이터 모델 및 CLI 설정 ──

@dataclass
class SearchConfig:
    '''탐색 설정 데이터를 담아두는 데이터 클래스(Data Class)입니다.
    reverse: 역순 탐색 여부, resume: 이어하기 여부, workers: 사용할 CPU 코어 수
    start_index: 탐색 시작 인덱스, end_index: 탐색 종료 인덱스'''
    reverse: bool
    resume: bool
    workers: int | None
    start_index: int
    end_index: int

def parse_args() -> SearchConfig:
    '''
    명령행 인자(Command Line Arguments)를 파싱하여 설정 객체를 반환합니다.
    
    Returns:
        SearchConfig: 파싱이 완료된 탐색 설정 정보 객체
    '''
    parser = argparse.ArgumentParser(description='화성 기지 비상 창고 암호 해독기')
    parser.add_argument('--reverse', action='store_true', help='뒷 번호부터 역순으로 암호를 탐색합니다.')
    parser.add_argument('--resume', action='store_true', help='이전 작업 지점부터 이어서 해독을 시작합니다.')
    parser.add_argument('--workers', type=int, default=None, help='사용할 CPU 코어 수를 임의로 지정합니다.')
    parser.add_argument('--start', type=str, default=None, help='탐색을 시작할 6자리 문자열 암호 (예: 000000)')
    parser.add_argument('--end', type=str, default=None, help='탐색을 종료할 6자리 문자열 암호 (예: zzzzzz)')
    parsed_args = parser.parse_args()
    
    start_idx = 0
    end_idx = BASE ** PASSWORD_LENGTH
    
    if parsed_args.start:
        start_idx = password_to_index(parsed_args.start)
    if parsed_args.end:
        # 사용자가 지정한 종료 암호까지 온전히 탐색(Inclusive)할 수 있도록 범위 끝(end_idx)에 1을 더해줍니다.
        end_idx = password_to_index(parsed_args.end) + 1
    if start_idx >= end_idx:
        raise ValueError('시작 범위가 종료 범위보다 크거나 같습니다.')
        
    return SearchConfig(
        reverse=parsed_args.reverse,
        resume=parsed_args.resume,
        workers=parsed_args.workers,
        start_index=start_idx,
        end_index=end_idx
    )

# ── 2. 유틸리티 및 암호 연산 (Utils & Math) ──

def format_elapsed_time(elapsed_seconds: float) -> str:
    '''
    경과 시간을 HH:MM:SS 포맷으로 변환합니다.
    
    Args:
        elapsed_seconds (float): 경과 시간 (초 단위)
        
    Returns:
        str: 'HH:MM:SS' 형식의 포맷팅된 문자열
    '''
    minutes, seconds = divmod(int(elapsed_seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'

def password_to_index(password: str) -> int:
    '''
    문자열 암호를 N진법 숫자로 치환하여 고유 인덱스를 생성합니다.
    
    Args:
        password (str): 6자리 영숫자 암호 문자열
        
    Returns:
        int: N진법으로 변환된 정수형 고유 인덱스
        
    Raises:
        ValueError: 비밀번호의 길이가 다르거나 유효하지 않은 문자가 포함된 경우
    '''
    password = password.lower()
    if len(password) != PASSWORD_LENGTH or any(char not in CHARSET for char in password):
        raise ValueError(f'비밀번호는 {PASSWORD_LENGTH}자리의 유효한 영숫자로만 구성되어야 합니다.')
    
    # 파이썬에 내장된 int() 함수를 사용하면 C언어 수준의 속도로 빠르게 N진법 문자열을 정수로 변환할 수 있습니다.
    return int(password, BASE)

def index_to_password(index: int) -> str:
    '''
    숫자 인덱스를 다시 문자열 암호로 변환합니다.
    
    Args:
        index (int): 변환할 숫자형 인덱스
        
    Returns:
        str: 복원된 6자리 문자열 암호
    '''
    chars = []
    temp = index
    for _ in range(PASSWORD_LENGTH):
        temp, remainder = divmod(temp, BASE)
        chars.append(CHARSET[remainder])
    return ''.join(reversed(chars))

def create_password_generator():
    '''
    특정 인덱스를 받아 즉시 바이트(bytes) 암호로 변환해 주는 최적화된 함수(클로저)를 반환합니다.
    
    Returns:
        function: 인덱스(int)를 인자로 받아 bytes 암호를 반환하는 발전기(Generator) 함수
    '''
    # N진법 변환 시 매번 거듭제곱 연산을 하면 느리므로, 각 자리의 가중치(Base^N)를 리스트로 미리 계산해 둡니다.
    powers = [BASE ** i for i in range(PASSWORD_LENGTH - 1, -1, -1)]
    charset_bytes = CHARSET.encode('utf-8')
    
    # 외부 변수(powers, charset_bytes)를 기억하는 클로저(Closure) 함수를 반환하여, 호출될 때마다 빠르고 독립적으로 연산하게 합니다.
    def generator(idx: int) -> bytes:
        return bytes([charset_bytes[(idx // p) % BASE] for p in powers])
        
    return generator

# ── 3. 파일 I/O 및 ZIP 처리 (File & Zip) ──

def save_checkpoint(reverse, total_attempts, positions, worker_ranges):
    '''
    진행 상황을 임시 파일을 거쳐 원자적(Atomic)으로 안전하게 저장합니다.
    
    Args:
        reverse (bool): 역순 탐색 여부
        total_attempts (int): 전체 누적 시도 횟수
        positions (list): 워커별 현재 탐색 위치 목록
        worker_ranges (list): 워커별 할당된 초기 탐색 범위 정보
    '''
    checkpoint_data = {
        'reverse': reverse,
        'cores': len(worker_ranges),
        'shared_count': total_attempts,
        'positions': list(positions),
        'tasks_info': worker_ranges
    }
    tmp_file = CHECKPOINT_FILE_PATH + '.tmp'
    # 원자적 쓰기(Atomic Write): 디스크에 쓰는 도중 전원이 나가거나 종료되어도 파일이 손상되지 않도록 임시 파일(.tmp)에 먼저 기록합니다.
    try:
        with open(tmp_file, 'w', encoding='utf-8') as raw_file:
            json.dump(checkpoint_data, raw_file, indent=4)
            raw_file.flush()
            # OS의 버퍼 캐시를 거치지 않고 디스크에 즉시(Sync) 쓰도록 강제하여 데이터 무결성을 보장합니다.
            os.fsync(raw_file.fileno()) 
        os.replace(tmp_file, CHECKPOINT_FILE_PATH) # 안전하게 기록이 끝난 임시 파일을 원래의 체크포인트 파일명으로 덮어씌웁니다.
    except OSError as e:
        print(f'[경고] 체크포인트 저장 중 오류 발생: {e}')

def extract_zip_info():
    '''
    ZIP 파일의 유효성을 검증하고 암호화 헤더와 체크 바이트를 추출합니다.
    
    Returns:
        tuple: (check_byte, encrypted_header)
            검증에 사용할 1바이트 기준값과 12바이트 암호화 헤더 데이터. 실패 시 (None, None) 반환.
    '''
    try:
        with zipfile.ZipFile(ZIP_FILE_PATH) as archive:
            if not archive.infolist():
                return None, None
            target_file_info = archive.infolist()[0]
            # ZipCrypto 규약: 데이터 디스크립터 플래그(0x08) 활성화 여부에 따라 
            # 검증용 1바이트(check_byte)를 파일 수정 시간 또는 CRC32에서 추출합니다.
            check_byte = (target_file_info._raw_time >> 8) & 0xFF if target_file_info.flag_bits & 0x08 else (target_file_info.CRC >> 24) & 0xFF
            
            with open(ZIP_FILE_PATH, 'rb') as raw_file:
                # 파일의 로컬 헤더 위치로 이동하여, 헤더 크기와 가변 필드 길이를 읽어옵니다.
                raw_file.seek(target_file_info.header_offset)
                file_header = raw_file.read(zipfile.sizeFileHeader)
                header_fields = struct.unpack(zipfile.structFileHeader, file_header)
                filename_length = header_fields[zipfile._FH_FILENAME_LENGTH]
                extra_field_length = header_fields[zipfile._FH_EXTRA_FIELD_LENGTH]
                # 로컬 헤더, 파일명, 추가 필드(Extra Field) 영역을 모두 건너뛰어, 실제 암호화된 12바이트 헤더의 시작 위치로 이동합니다.
                raw_file.seek(target_file_info.header_offset + zipfile.sizeFileHeader + filename_length + extra_field_length)
                encrypted_header = raw_file.read(12)
        return check_byte, encrypted_header
    except (zipfile.BadZipFile, OSError, struct.error) as e:
        print(f'[경고] ZIP 파일 읽기 오류: {e}')
        return None, None

def test_password(archive, target_file_info, candidate_password_bytes, encrypted_header, check_byte):
    '''
    ZipCrypto의 12바이트 헤더 검증 기법을 활용하여 비밀번호를 고속으로 테스트합니다.
    
    Args:
        archive (zipfile.ZipFile): 검사할 ZIP 파일 객체
        target_file_info (zipfile.ZipInfo): 타겟 파일의 정보 구조체
        candidate_password_bytes (bytes): 테스트할 암호 후보 바이트열
        encrypted_header (bytes): 원본 ZIP 파일의 12바이트 암호화 헤더
        check_byte (int): 헤더 복호화 성공 여부를 판가름할 기준 바이트
        
    Returns:
        bool: 암호가 일치하여 압축 해제에 성공하면 True, 아니면 False
    '''
    # ZipDecrypter로 12바이트 헤더만 복호화한 후, 마지막 1바이트가 check_byte와 일치하는지 확인합니다.
    # 이 방법으로 무거운 압축 해제 과정을 거치지 않고도 오답의 99.6%를 1차적으로 걸러낼 수 있습니다.
    decrypter = zipfile._ZipDecrypter(candidate_password_bytes)
    if decrypter(encrypted_header)[11] == check_byte:
        try:
            with archive.open(target_file_info, pwd=candidate_password_bytes) as zipped_file:
                # 1차 검증을 통과한 후보 암호로 실제 파일 압축 해제를 시도합니다. 내부 CRC32 해시 검사까지 통과하면 최종 정답입니다.
                zipped_file.read()
            return True
        except (RuntimeError, zipfile.BadZipFile, zlib.error):
            # 1차 헤더 검증은 우연히 통과했지만 실제 암호는 틀려서 압축 해제 중 에러가 난 경우이므로 무시합니다.
            pass
    return False

# ── 4. 백그라운드 워커 (Multiprocessing Worker) ──

def flush_local_attempts(local_attempts: int, total_attempts_counter: Any, counter_lock: Any) -> int:
    '''
    로컬에 누적된 시도 횟수를 공유 카운터에 안전하게 반영하고 0으로 초기화하여 반환합니다.
    
    Args:
        local_attempts (int): 현재 워커에 누적된 시도 횟수
        total_attempts_counter (Value): 멀티프로세싱 공유 메모리 카운터 객체
        counter_lock (Lock): 카운터 동기화 락 객체
        
    Returns:
        int: 초기화된 횟수 (항상 0 반환)
    '''
    if local_attempts > 0:
        with counter_lock:
            total_attempts_counter.value += local_attempts
    return 0

def search_password_chunk(
    worker_id: int, step: int, end_condition: int, check_byte: int, 
    encrypted_header: bytes, total_attempts_counter: Any, counter_lock: Any, 
    worker_positions: Any
):
    '''
    [백그라운드 워커] 주어진 구간 안에서 암호를 반복 검증하고 주기적으로 공유 변수에 
    진행 상황(시도 횟수, 현재 위치)을 업데이트합니다.
    '''
    try:
        with zipfile.ZipFile(ZIP_FILE_PATH, 'r') as archive:
            if not archive.infolist():
                return None
            target_file_info = archive.infolist()[0]
            local_attempts = 0
            
            # 메인 프로세스에서 계산해 준 시작, 종료, 증감(step) 값을 바탕으로 반복문(range)을 생성합니다.
            start_position = worker_positions[worker_id]
            index_iterator = range(start_position, end_condition, step)
            
            # 인덱스 번호를 받아 바로 암호 바이트열로 변환해 주는 최적화된 함수(클로저)를 생성하여, 반복문 안에서 빠르게 암호 후보를 만들어 냅니다.
            generate_password = create_password_generator()
            
            for idx in index_iterator:
                local_attempts += 1
                
                candidate_password_bytes = generate_password(idx)
                
                if test_password(archive, target_file_info, candidate_password_bytes, encrypted_header, check_byte):
                    local_attempts = flush_local_attempts(local_attempts, total_attempts_counter, counter_lock)
                    return candidate_password_bytes.decode('utf-8') # 정답 바이트열을 문자열(str)로 복원하여 반환합니다.
                
                if local_attempts >= 100000:
                    local_attempts = flush_local_attempts(local_attempts, total_attempts_counter, counter_lock)
                    # 탐색이 중단되었다 재시작될 때 이미 검사한 곳을 또 검사하지 않도록 다음 위치(idx + step)를 기록해 둡니다.
                    worker_positions[worker_id] = idx + step 
            
            local_attempts = flush_local_attempts(local_attempts, total_attempts_counter, counter_lock)
            
            # [중요] 해당 코어가 할당받은 구역의 탐색을 모두 마쳤다면, 나중에 이어하기 시 이 구역을 아예 건너뛰도록 종료 위치로 덮어씁니다.
            worker_positions[worker_id] = end_condition
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'\n[경고] 작업자 {worker_id}에서 예기치 않은 에러가 발생하여 탐색을 중단합니다: {e}')
    return None

# ── 5. 메인 오케스트레이터 (Orchestrator) ──

def setup_search_environment(config):
    '''
    체크포인트를 로드하거나, 없을 경우 새롭게 작업자별 탐색 범위를 분할합니다.
    
    Args:
        config (SearchConfig): 명령행 인자로 생성된 설정 객체
        
    Returns:
        tuple: (worker_count, restored_attempts, positions, worker_ranges, is_reverse)
    '''
    if config.resume:
        try:
            with open(CHECKPOINT_FILE_PATH, 'r', encoding='utf-8') as raw_file:
                checkpoint_data = json.load(raw_file)
            is_reverse = checkpoint_data['reverse']
            worker_count = checkpoint_data['cores']
            restored_attempts = checkpoint_data['shared_count']
            worker_ranges = checkpoint_data['tasks_info']
            positions = checkpoint_data['positions']
            
            print('\n--- 체크포인트에서 이어하기를 시도합니다 ---')
            print(f'복구된 시도 횟수: {restored_attempts:,}회')
            print(f'복구된 작업 코어 수: {worker_count}개\n')
            
            # 체크포인트 로드에 성공하면 곧바로 값을 반환하고 함수를 종료합니다. (조기 반환 패턴)
            return worker_count, restored_attempts, positions, worker_ranges, is_reverse
        except FileNotFoundError:
            print('\n[안내] 저장된 체크포인트가 없습니다. 처음부터 탐색을 시작합니다.')
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f'\n[경고] 체크포인트 로드 실패 ({e}). 처음부터 다시 시작합니다.')

    # --- 체크포인트가 없거나 로드에 실패하여 처음부터 탐색을 시작할 때의 초기화 로직 ---
    requested_workers = config.workers if config.workers else multiprocessing.cpu_count()
    total_search_space = config.end_index - config.start_index
    # 남은 경우의 수보다 할당된 코어 수가 더 많다면, 낭비를 막기 위해 작업자 수를 줄입니다.
    worker_count = min(requested_workers, total_search_space)
    
    worker_ranges = []
    positions = [0] * worker_count
    is_reverse = config.reverse
    restored_attempts = 0
    
    # 전체 탐색 범위를 작업자(코어) 수만큼 최대한 균등하게 나누어 분배합니다.
    base_chunk, remainder = divmod(total_search_space, worker_count)
    cursor = config.start_index
    for i in range(worker_count):
        chunk_size = base_chunk + (1 if i < remainder else 0)
        s = cursor
        e = cursor + chunk_size
        worker_ranges.append({'start': s, 'end': e})
        positions[i] = e - 1 if is_reverse else s
        cursor = e
            
    return worker_count, restored_attempts, positions, worker_ranges, is_reverse

def monitor_workers(async_results, reverse, total_attempts_counter, worker_positions, worker_ranges, started_at):
    '''
    [메인 프로세스] Pool.apply_async로 비동기 실행된 작업자들의 결과를 주기적으로 
    폴링(Polling)하며 모니터링하고 체크포인트를 저장합니다.
    '''
    found_password = None
    last_checkpoint_saved_at = time.time()
    # 이미 결과를 가져온(get) 비동기 작업을 중복 확인하지 않도록 처리 완료 상태를 배열로 관리합니다.
    processed_results = [False] * len(async_results)
    
    while True:
        all_tasks_processed = True
        for i, res in enumerate(async_results):
            if not processed_results[i]:
                if res.ready():
                    result = res.get() # 작업이 끝났다면 get()을 한 번만 호출하여 결과를 가져옵니다.
                    processed_results[i] = True
                    if result:
                        found_password = result
                        break # 암호를 성공적으로 찾은 워커가 있다면 즉시 모니터링 루프를 중단합니다.
                else:
                    all_tasks_processed = False # 하나라도 덜 끝난 작업이 있으면 모두 완료된 것이 아님을 표시합니다.
        
        if found_password or all_tasks_processed:
            break
        
        # 공유 객체(Value) 접근 시 프로세스 통신(IPC) 비용이 발생하므로, 루프 한 번당 한 번만 읽어서 로컬 변수에 복사해 씁니다.
        current_attempts = total_attempts_counter.value
        
        # 성능 저하를 막기 위해 5초 단위로만 각 작업자의 진행 상황을 모아서 체크포인트 파일에 저장합니다.
        now = time.time()
        if now - last_checkpoint_saved_at > 5.0:
            save_checkpoint(reverse, current_attempts, worker_positions, worker_ranges)
            last_checkpoint_saved_at = now
        
        # 사용자가 터미널에서 작업이 멈추지 않았음을 알 수 있도록 진행 상황을 덮어쓰기(\r)로 출력합니다.
        elapsed = time.time() - started_at
        print(f'\r[해독 중] 시도: {current_attempts:,}회 | 진행 시간: {format_elapsed_time(elapsed)}', end='', flush=True)
        time.sleep(0.5)
        
    # 모니터링이 끝나는 시점의 최종 횟수까지 같이 반환하여, 밖에서 Manager 객체를 또 조회하지 않도록 최적화합니다.
    return found_password, all(processed_results), total_attempts_counter.value

def handle_search_result(found_password, total_attempts, started_at):
    '''
    해독 결과를 화면에 출력하고 파일로 저장합니다.
    
    Args:
        found_password (str | None): 찾은 비밀번호 문자열 (실패 시 None)
        total_attempts (int): 탐색에 소요된 최종 시도 횟수
        started_at (float): 스크립트 실행이 시작된 시간 (time.time())
    '''
    elapsed_time = time.time() - started_at
    if found_password:
        print(f'\n\n비밀번호를 찾았습니다!: {found_password}')
        print(f'최종 반복 회수: {total_attempts:,}회')
        
        try:
            with open(PASSWORD_FILE_PATH, 'w', encoding='utf-8') as raw_file:
                raw_file.write(found_password)
        except OSError as e:
            print(f'[오류] 비밀번호 저장 실패: {e}')
    else:
        print('\n\n암호 해독 실패.')
        
    print(f'총 진행 시간: {format_elapsed_time(elapsed_time)}')

def unlock_zip(config):
    '''
    비상 창고의 암호를 해독하기 위한 메인 오케스트레이션(Orchestration) 함수입니다.
    
    Args:
        config (SearchConfig): 명령행 인자로 구성된 설정 객체
    '''
    started_at = time.time()
    
    print('--- 화성 기지 비상 창고 암호 해독 시작 ---')
    print(f'시작 시간: {time.ctime(started_at)}')
    
    check_byte, encrypted_header = extract_zip_info()
    if check_byte is None:
        return

    # 여러 작업자(프로세스)가 동시에 접근하고 수정해도 안전한 공유 메모리 공간을 Manager()를 통해 생성합니다.
    with multiprocessing.Manager() as manager:
        worker_count, restored_attempts, positions, worker_ranges, is_reverse = setup_search_environment(config)
                
        # 상태 공유를 위한 프로세스 안전(Thread-safe) 변수들(총 시도 횟수, 락, 현재 위치 배열)을 생성합니다.
        total_attempts_counter = manager.Value('Q', restored_attempts)
        counter_lock = manager.Lock()
        worker_positions = manager.list(positions)
                
        # 작업 구역 분배가 끝나고 확정된 실제 탐색 정보를 사용자 화면에 명확하게 표시합니다.
        actual_start = index_to_password(worker_ranges[0]['start'])
        actual_end = index_to_password(worker_ranges[-1]['end'] - 1)
        print(f'\n[탐색 설정 정보]')
        print(f'탐색 범위: {actual_start} ~ {actual_end}')
        print(f'탐색 방향: {"역순 (Reverse)" if is_reverse else "정방향 (Forward)"}')
        print(f'할당 코어: {worker_count}개\n')
                
        worker_args = []
        step = -1 if is_reverse else 1
        for i in range(worker_count):
            worker_range = worker_ranges[i]
            end_condition = (worker_range['start'] - 1) if is_reverse else worker_range['end']
            worker_args.append((i, step, end_condition, check_byte, encrypted_header, total_attempts_counter, counter_lock, worker_positions))

        # 설정된 코어 수만큼 백그라운드 프로세스 풀(Pool)을 띄우고, 각자 맡은 구역을 비동기적(apply_async)으로 실행시킵니다.
        with multiprocessing.Pool(processes=worker_count) as pool:
            async_results = [pool.apply_async(search_password_chunk, args) for args in worker_args]
            
            try:
                found_password, is_all_completed, final_attempts = monitor_workers(
                    async_results, is_reverse, total_attempts_counter, 
                    worker_positions, worker_ranges, started_at
                )
            except KeyboardInterrupt:
                final_attempts = total_attempts_counter.value
                print('\n\n[경고] 사용자에 의해 해독이 중단되었습니다. 진행 상황을 저장합니다...')
                try:
                    save_checkpoint(is_reverse, final_attempts, worker_positions, worker_ranges)
                    print('저장 완료! 다음 실행 시 `--resume` 옵션을 주면 이어서 실행됩니다.')
                except Exception as e:
                    print(f'체크포인트 저장 중 오류 발생: {e}')
            except Exception as e:
                print(f'\n\n[오류] 해독 도중 예기치 않은 에러가 발생했습니다: {e}')
            else:
                # 작업이 오류 없이 끝났을 경우(정답 발견 or 전체 탐색 완료)의 후속 처리입니다.
                if found_password or is_all_completed:
                    try:
                        os.remove(CHECKPOINT_FILE_PATH) # 해독이 완전히 끝났으므로 더 이상 필요 없는 임시 체크포인트 파일을 지웁니다.
                    except FileNotFoundError:
                        pass # 파일이 이미 삭제되었거나 존재하지 않는 에러(FileNotFound)는 조용히 무시합니다. (EAFP 패턴)
                    except OSError as e:
                        print(f'\n[경고] 체크포인트 파일 삭제 실패: {e}')
                handle_search_result(found_password, final_attempts, started_at)
            finally:
                pool.terminate() # 예외가 나든 완료되든, 마지막에는 반드시 남은 작업자 프로세스들을 강제 종료하고 메모리 자원을 OS에 반환합니다.
                pool.join()

# ── 6. 진입점 (Entry Point) ──

def main():
    try:
        config = parse_args()
        unlock_zip(config)
    except ValueError as e:
        print(f'입력 범위 오류: {e}')

if __name__ == '__main__':
    # Windows OS에서 파이썬 멀티프로세싱 코드가 무한 증식하는 버그를 막기 위한 필수 보호 코드입니다.
    multiprocessing.freeze_support()
    main()