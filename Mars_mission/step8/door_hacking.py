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

# 실행 중인 스크립트 파일의 부모 디렉토리를 절대 경로로 구하여, 
# 스크립트 실행 위치와 무관하게 항상 동일한 폴더에 파일이 저장되도록 보장합니다.
BASE_DIR = Path(__file__).resolve().parent
ZIP_FILE_PATH = str(BASE_DIR / 'emergency_storage_key.zip')
PASSWORD_FILE_PATH = str(BASE_DIR / 'password.txt')
CHECKPOINT_FILE_PATH = str(BASE_DIR / 'checkpoint.json')

# 암호 해독에 사용할 문자열 집합(숫자 + 영소문자)과 암호 길이를 설정합니다.
CHARSET = string.digits + string.ascii_lowercase
PASSWORD_LENGTH = 6
BASE = len(CHARSET) # 36진법(숫자 10개 + 알파벳 26개) 변환을 위한 기준 값

@dataclass
class SearchConfig:
    '''탐색 설정 데이터를 담아두는 클래스입니다.'''
    zip_path: str
    password_path: str
    checkpoint_path: str
    charset: str
    password_length: int
    base: int
    reverse: bool
    resume: bool
    workers: int | None
    start_index: int
    end_index: int

def format_elapsed_time(elapsed_seconds):
    '''경과 시간을 HH:MM:SS 포맷으로 변환합니다.'''
    minutes, seconds = divmod(int(elapsed_seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'

def password_to_index(password: str, charset: str, password_length: int) -> int:
    '''
    문자열 암호를 n진법 숫자로 치환하여 고유 인덱스를 생성합니다.
    '''
    if len(password) != password_length:
        raise ValueError(f'비밀번호 길이는 {password_length}자여야 합니다.')
    
    value = 0
    base = len(charset)
    for char in password:
        if char not in charset:
            raise ValueError(f"'{char}'는 유효한 문자가 아닙니다.")
        value = (value * base) + charset.index(char)
    return value

def index_to_password(index: int, charset: str, password_length: int) -> str:
    '''숫자 인덱스를 다시 문자열 암호로 변환합니다.'''
    chars = []
    base = len(charset)
    temp = index
    for _ in range(password_length):
        temp, remainder = divmod(temp, base)
        chars.append(charset[remainder])
    return ''.join(reversed(chars))

def save_checkpoint(config, worker_count, total_attempts_counter, positions, worker_ranges):
    '''진행 상황을 임시 파일을 거쳐 원자적으로 안전하게 저장합니다.'''
    checkpoint_data = {
        'reverse': config.reverse,
        'cores': worker_count,
        'shared_count': total_attempts_counter.value,
        'positions': list(positions),
        'tasks_info': worker_ranges
    }
    tmp_file = config.checkpoint_path + '.tmp'
    # 원자적 쓰기(Atomic Write) 패턴: 쓰기 도중 프로그램이 종료되어도 파일이 손상되지 않도록 임시 파일에 먼저 씁니다.
    try:
        with open(tmp_file, 'w', encoding='utf-8') as raw_file:
            json.dump(checkpoint_data, raw_file, indent=4)
            raw_file.flush()
            # OS 캐시를 무시하고 디스크에 즉시 기록하도록 강제합니다.
            os.fsync(raw_file.fileno()) 
        os.replace(tmp_file, config.checkpoint_path) # 쓰기가 완료되면 원본 파일과 교체합니다.
    except OSError as e:
        print(f'[경고] 체크포인트 저장 중 오류 발생: {e}')

def extract_zip_info(zip_path):
    '''ZIP 파일의 유효성을 검증하고 암호화 헤더와 체크 바이트를 추출합니다.'''
    try:
        with zipfile.ZipFile(zip_path) as archive:
            if not archive.infolist():
                return None, None
            target_file_info = archive.infolist()[0]
            # ZIP 전통 암호화 규약(ZipCrypto)에 따라, 플래그 비트 0x08(데이터 디스크립터 사용) 여부에 따라
            # 복호화 검증에 사용할 기준 바이트(check_byte)가 파일 수정 시간의 일부인지, CRC32의 일부인지 결정됩니다.
            check_byte = (target_file_info._raw_time >> 8) & 0xFF if target_file_info.flag_bits & 0x08 else (target_file_info.CRC >> 24) & 0xFF
            
            with open(zip_path, 'rb') as raw_file:
                # 로컬 파일 헤더의 오프셋으로 이동하여 헤더 구조체의 길이를 파악합니다.
                raw_file.seek(target_file_info.header_offset)
                file_header = raw_file.read(zipfile.sizeFileHeader)
                header_fields = struct.unpack(zipfile.structFileHeader, file_header)
                filename_length = header_fields[zipfile._FH_FILENAME_LENGTH]
                extra_field_length = header_fields[zipfile._FH_EXTRA_FIELD_LENGTH]
                # 로컬 파일 헤더와 파일명, 추가 필드를 건너뛰면 실제 암호화된 데이터의 시작점(12바이트 암호화 헤더)이 나옵니다.
                raw_file.seek(target_file_info.header_offset + zipfile.sizeFileHeader + filename_length + extra_field_length)
                encrypted_header = raw_file.read(12)
        return check_byte, encrypted_header
    except (zipfile.BadZipFile, OSError, struct.error) as e:
        print(f'[경고] ZIP 파일 읽기 오류: {e}')
        return None, None

def test_password(archive, target_file_info, candidate_password_bytes, encrypted_header, check_byte):
    '''ZipCrypto의 12바이트 헤더 검증 기법을 활용하여 비밀번호를 고속으로 테스트합니다.'''
    # 비밀번호 후보로 ZipDecrypter를 초기화한 뒤 12바이트 헤더를 복호화합니다.
    # 복호화된 헤더의 12번째 바이트(인덱스 11)가 check_byte와 일치하는지 먼저 검사하여, 99.6%의 틀린 암호를 즉시 걸러냅니다.
    decrypter = zipfile._ZipDecrypter(candidate_password_bytes)
    if decrypter(encrypted_header)[11] == check_byte:
        try:
            with archive.open(target_file_info, pwd=candidate_password_bytes) as zipped_file:
                # 암호가 맞다면 정상적으로 압축이 풀려야 하므로 read()를 시도합니다. CRC32 검사까지 통과하면 True입니다.
                zipped_file.read()
            return True
        except (RuntimeError, zipfile.BadZipFile, zlib.error):
            # 압축 해제 중 에러가 발생하면 우연히 헤더만 일치한 틀린 암호이므로 무시합니다.
            pass
    return False

def setup_search_environment(config, manager):
    '''체크포인트를 로드하거나, 없을 경우 새롭게 작업자별 탐색 범위를 분할합니다.'''
    # 다중 프로세스 환경에서 안전하게 값을 공유하고 갱신하기 위해 Manager의 Value, Lock, List를 사용합니다.
    total_attempts_counter = manager.Value('Q', 0)
    counter_lock = manager.Lock()
    worker_ranges = []
    
    if config.resume:
        if os.path.exists(config.checkpoint_path):
            print('\n--- 체크포인트에서 이어하기를 시도합니다 ---')
            try:
                with open(config.checkpoint_path, 'r', encoding='utf-8') as raw_file:
                    checkpoint_data = json.load(raw_file)
                config.reverse = checkpoint_data['reverse']
                worker_count = checkpoint_data['cores']
                total_attempts_counter.value = checkpoint_data['shared_count']
                worker_ranges = checkpoint_data['tasks_info']
                worker_positions = manager.list(checkpoint_data['positions'])
                print(f'복구된 시도 횟수: {total_attempts_counter.value:,}회')
                print(f'복구된 작업 코어 수: {worker_count}개\n')
            except (OSError, json.JSONDecodeError, KeyError) as e:
                print(f'[경고] 체크포인트 로드 실패 ({e}). 처음부터 다시 시작합니다.')
                config.resume = False # 실패 시 resume 플래그를 꺼서 새로 시작하도록 강제
        else:
            print('\n[안내] 저장된 체크포인트가 없습니다. 처음부터 탐색을 시작합니다.')
            config.resume = False

    # config.resume가 False이거나, resume 시도에 실패했을 경우 새로 환경을 구성합니다.
    if not config.resume:
        requested_workers = config.workers if config.workers else multiprocessing.cpu_count()
        total_search_space = config.end_index - config.start_index
        # 탐색 공간보다 작업자 수가 많아지지 않도록 조정하여 낭비를 막습니다.
        worker_count = min(requested_workers, total_search_space)
        print(f'할당된 작업 코어 수: {worker_count}개\n')
        worker_positions = manager.list([0] * worker_count)
        
        # divmod를 사용하여 작업량을 최대한 균등하게 분배합니다.
        base_chunk, remainder = divmod(total_search_space, worker_count)
        cursor = config.start_index
        for i in range(worker_count):
            chunk_size = base_chunk + (1 if i < remainder else 0)
            s = cursor
            e = cursor + chunk_size
            worker_ranges.append({'start': s, 'end': e})
            worker_positions[i] = e - 1 if config.reverse else s
            cursor = e
            
    return worker_count, total_attempts_counter, counter_lock, worker_positions, worker_ranges

def handle_search_result(found_password, total_attempts_counter, started_at, config):
    '''해독 결과를 화면에 출력하고 파일로 저장합니다.'''
    elapsed_time = time.time() - started_at
    if found_password:
        print(f'\n\n비밀번호를 찾았습니다!: {found_password}')
        print(f'최종 반복 회수: {total_attempts_counter.value:,}회')
        print(f'총 진행 시간: {format_elapsed_time(elapsed_time)}')
        
        try:
            with open(config.password_path, 'w', encoding='utf-8') as raw_file:
                raw_file.write(found_password)
        except OSError as e:
            print(f'[오류] 비밀번호 저장 실패: {e}')
    else:
        print('\n\n암호 해독 실패.')
        print(f'총 진행 시간: {format_elapsed_time(elapsed_time)}')

def create_password_generator(length: int, base_val: int, charset: str):
    '''특정 인덱스를 받아 즉시 바이트(bytes) 비밀번호로 변환해 주는 최적화된 함수(클로저)를 반환합니다.'''
    # 매번 제곱 연산을 하지 않도록 자리수별 가중치(powers)를 미리 계산해 메모리에 올려둡니다.
    powers = [base_val ** i for i in range(length - 1, -1, -1)]
    charset_bytes = charset.encode('utf-8')
    
    # 파이썬의 동적 바인딩을 이용해 외부 변수(powers, charset_bytes)를 참조하는 내부 함수를 반환합니다.
    def generator(idx: int) -> bytes:
        return bytes([charset_bytes[(idx // p) % base_val] for p in powers])
        
    return generator

def search_password_chunk(
    worker_id: int, zip_path: str, start_idx: int, end_idx: int, check_byte: int, 
    encrypted_header: bytes, total_attempts_counter: Any, counter_lock: Any, reverse: bool, 
    worker_positions: Any, charset: str, password_length: int, base: int
):
    '''작업자: 암호를 검증하고 주기적으로 공유 변수에 진행 상황을 업데이트합니다.'''
    try:
        with zipfile.ZipFile(zip_path, 'r') as archive:
            if not archive.infolist():
                return None
            target_file_info = archive.infolist()[0]
            local_attempts = 0
            
            # 할당받은 작업 구간(start_position ~ 끝) 내에서 순차적 또는 역순으로 탐색을 진행합니다.
            start_position = worker_positions[worker_id]
            index_iterator = range(start_position, start_idx - 1, -1) if reverse else range(start_position, end_idx)
            
            generate_password = create_password_generator(password_length, base, charset)
            
            for idx in index_iterator:
                # 성능 저하를 막기 위해 매번 lock을 걸지 않고 프로세스 내부의 로컬 변수에 먼저 누적합니다.
                local_attempts += 1
                
                candidate_password_bytes = generate_password(idx)
                
                if test_password(archive, target_file_info, candidate_password_bytes, encrypted_header, check_byte):
                    with counter_lock:
                        total_attempts_counter.value += local_attempts
                    return candidate_password_bytes.decode('utf-8') # 찾은 후 문자열로 복원하여 반환
                
                # 10만 번 시도마다 로컬에 쌓인 횟수를 메인 프로세스의 공유 카운터에 반영하고 현재 위치를 기록합니다.
                if local_attempts >= 100000:
                    with counter_lock:
                        total_attempts_counter.value += local_attempts
                    local_attempts = 0
                    # 중복 탐색을 막기 위해 현재 위치의 '다음' 위치를 기록합니다.
                    worker_positions[worker_id] = idx - 1 if reverse else idx + 1 
            
            # 남은 자투리 횟수 최종 업데이트
            if local_attempts > 0:
                with counter_lock:
                    total_attempts_counter.value += local_attempts
            
            # [중요] 할당된 작업을 모두 마쳤을 경우, 재시작(Resume) 시 해당 구간을 건너뛰도록 위치를 끝으로 기록합니다.
            worker_positions[worker_id] = (start_idx - 1) if reverse else end_idx
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'\n[경고] 작업자 {worker_id}에서 예기치 않은 에러가 발생하여 탐색을 중단합니다: {e}')
    return None

def monitor_workers(async_results, config, worker_count, total_attempts_counter, worker_positions, worker_ranges, started_at):
    '''Pool.apply_async로 비동기 실행된 작업자들의 결과를 주기적으로 폴링(Polling)하며 모니터링합니다.'''
    found_password = None
    last_checkpoint_saved_at = time.time()
    # get() 메서드를 여러 번 호출하는 오류를 막기 위해 각 작업의 처리 여부를 기록합니다.
    processed_results = [False] * len(async_results)
    
    while True:
        all_tasks_processed = True
        for i, res in enumerate(async_results):
            if not processed_results[i]: # 아직 처리되지 않은 결과만 확인
                if res.ready():
                    result = res.get() # get()은 여기서 단 한번만 호출됩니다.
                    processed_results[i] = True
                    if result:
                        found_password = result
                        break # 암호를 찾았으면 루프 즉시 탈출
                else:
                    all_tasks_processed = False # 아직 실행 중인 작업이 있음
        
        if found_password or all_tasks_processed:
            break
        
        # 일정 주기(5초)마다 메인 프로세스가 모든 작업자의 진행 상황을 취합하여 체크포인트 파일에 저장합니다.
        now = time.time()
        if now - last_checkpoint_saved_at > 5.0:
            save_checkpoint(config, worker_count, total_attempts_counter, worker_positions, worker_ranges)
            last_checkpoint_saved_at = now
        
        # 실시간 생존 신고 출력
        elapsed = time.time() - started_at
        current_total = total_attempts_counter.value
        print(f'\r[해독 중] 시도: {current_total:,}회 | 진행 시간: {format_elapsed_time(elapsed)}', end='', flush=True)
        time.sleep(0.5)
        
    return found_password, all(processed_results)

def unlock_zip(config):
    '''비상 창고의 암호를 해독하기 위한 메인 오케스트레이션 함수입니다.'''
    started_at = time.time()
    
    print('--- 화성 기지 비상 창고 암호 해독 시작 ---')
    print(f'시작 시간: {time.ctime(started_at)}')
    start_str = index_to_password(config.start_index, config.charset, config.password_length)
    end_str = index_to_password(config.end_index - 1, config.charset, config.password_length)
    print(f'탐색 범위: {start_str} ~ {end_str}')
    print(f'탐색 방향: {"역순 (Reverse)" if config.reverse else "정방향 (Forward)"}')
    print(f'할당 코어: {config.workers if config.workers else "자동 (전체 사용)"}')
    
    if not os.path.exists(config.zip_path):
        print(f'오류: {config.zip_path} 파일이 없습니다.')
        return

    check_byte, encrypted_header = extract_zip_info(config.zip_path)
    if check_byte is None:
        print(f'오류: {config.zip_path} 파일이 손상되었거나 비어있습니다.')
        return

    # Manager 객체를 통해 여러 프로세스가 동시에 접근해도 안전한 공유 메모리 공간을 생성합니다.
    manager = multiprocessing.Manager()
    worker_count, total_attempts_counter, counter_lock, worker_positions, worker_ranges = setup_search_environment(config, manager)
            
    worker_args = []
    for i in range(worker_count):
        worker_range = worker_ranges[i]
        worker_args.append((i, config.zip_path, worker_range['start'], worker_range['end'], check_byte, encrypted_header, total_attempts_counter, counter_lock, config.reverse, worker_positions, config.charset, config.password_length, config.base))

    # 작업자 프로세스를 관리할 Pool을 생성하고, 비동기 방식(apply_async)으로 각 코어에 작업을 분배합니다.
    with multiprocessing.Pool(processes=worker_count) as pool:
        async_results = [pool.apply_async(search_password_chunk, args) for args in worker_args]
        
        try:
            found_password, is_all_completed = monitor_workers(
                async_results, config, worker_count, total_attempts_counter, 
                worker_positions, worker_ranges, started_at
            )
        except KeyboardInterrupt:
            print('\n\n[경고] 사용자에 의해 해독이 중단되었습니다. 진행 상황을 저장합니다...')
            try:
                save_checkpoint(config, worker_count, total_attempts_counter, worker_positions, worker_ranges)
                print('저장 완료! 다음 실행 시 `--resume` 옵션을 주면 이어서 실행됩니다.')
            except Exception as e:
                print(f'체크포인트 저장 중 오류 발생: {e}')
        except Exception as e:
            print(f'\n\n[오류] 해독 도중 예기치 않은 에러가 발생했습니다: {e}')
        else:
            # 정상 종료 시 결과 처리
            if found_password or is_all_completed:
                try:
                    if os.path.exists(config.checkpoint_path):
                        os.remove(config.checkpoint_path) # 완료 후엔 체크포인트 삭제
                except OSError as e:
                    print(f'\n[경고] 체크포인트 파일 삭제 실패: {e}')
            handle_search_result(found_password, total_attempts_counter, started_at, config)
        finally:
            pool.terminate() # 어떤 상황이든 마지막엔 남은 작업자 프로세스 강제 종료 및 자원 반환
            pool.join()

def parse_args() -> SearchConfig:
    '''명령행 인자를 파싱하여 설정 객체를 반환합니다.'''
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
        start_idx = password_to_index(parsed_args.start, CHARSET, PASSWORD_LENGTH)
    if parsed_args.end:
        end_idx = password_to_index(parsed_args.end, CHARSET, PASSWORD_LENGTH)
    if start_idx >= end_idx:
        raise ValueError('시작 범위가 종료 범위보다 크거나 같습니다.')
        
    return SearchConfig(
        zip_path=ZIP_FILE_PATH,
        password_path=PASSWORD_FILE_PATH,
        checkpoint_path=CHECKPOINT_FILE_PATH,
        charset=CHARSET,
        password_length=PASSWORD_LENGTH,
        base=BASE,
        reverse=parsed_args.reverse,
        resume=parsed_args.resume,
        workers=parsed_args.workers,
        start_index=start_idx,
        end_index=end_idx
    )

def main():
    try:
        config = parse_args()
        unlock_zip(config)
    except ValueError as e:
        print(f'입력 범위 오류: {e}')

if __name__ == '__main__':
    # Windows 환경에서 멀티프로세싱을 안정적으로 실행하기 위해 freeze_support()를 호출합니다.
    multiprocessing.freeze_support()
    main()