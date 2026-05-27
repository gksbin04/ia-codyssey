import wave
import struct
import csv
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import pyaudio
except ImportError:
    print('PyAudio 패키지가 필요합니다.')
    print('다음 명령어로 설치해주세요: pip install pyaudio')
    exit(1)

try:
    import speech_recognition
except ImportError:
    print('SpeechRecognition 패키지가 필요합니다.')
    print('다음 명령어로 설치해주세요: pip install SpeechRecognition')
    exit(1)


class AudioRecorder:
    """마이크를 인식하고 음성을 녹음하여 파일로 저장하는 클래스입니다."""
    
    def __init__(self, record_dir: str = 'records') -> None:
        self.record_dir = Path(record_dir)
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        
        # 하위에 records 폴더가 없으면 새로 생성합니다.
        self.record_dir.mkdir(parents=True, exist_ok=True)

    def record_audio(self) -> None:
        """시스템 마이크를 통해 사용자가 중단할 때까지 음성을 녹음한 후 파일명을 입력받아 저장합니다."""
        audio = pyaudio.PyAudio()
        
        stream = audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print('녹음을 시작합니다... (종료하려면 "q" 키를 누르세요)')
        frames = []
        
        try:
            while True:
                data = stream.read(self.chunk)
                frames.append(data)
                
                # --- 현재 볼륨 크기를 계산하여 시각적으로 표시 ---
                samples = struct.unpack(f'{len(data)//2}h', data)
                volume = sum(abs(x) for x in samples) // len(samples)
                    
                level = min(50, int(volume / 200))
                print(f'\r[음성 감지] {"*" * level:<50}', end='', flush=True)
                
                if msvcrt and msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key.lower() == b'q':
                        while msvcrt.kbhit(): msvcrt.getch()  # 버퍼 비우기
                        print('\n[녹음 중단] 사용자의 요청으로 녹음이 조기 종료되었습니다.')
                        break
        except KeyboardInterrupt:
            print('\n[녹음 강제 중단] Ctrl+C 입력이 감지되었습니다. 지금까지의 데이터를 안전하게 저장합니다.')
            
        print('\n녹음이 완료되었습니다.')
        
        try:
            stream.stop_stream()
            stream.close()
        finally:
            audio.terminate()
        
        now = datetime.now()
        # 파일 이름 포맷: 년월일-시간분초 (추출 전 임시 파일명으로 먼저 저장)
        base_filename = now.strftime('%Y%m%d-%H%M%S')
            
        date_folder = self.record_dir / now.strftime('%Y') / now.strftime('%m') / now.strftime('%d')
        date_folder.mkdir(parents=True, exist_ok=True)
            
        filepath = date_folder / f'{base_filename}.wav'
        
        counter = 1
        while filepath.exists():
            filepath = date_folder / f'{base_filename}_{counter}.wav'
            counter += 1
            
        with wave.open(str(filepath), 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            
        print(f'\n[알림] 오디오 임시 저장이 완료되었습니다. 이어서 텍스트 추출(STT)을 자동으로 시작합니다.')
        
        # 1. 방금 녹음한 파일로 STT 자동 추출 실행
        rel_path = filepath.relative_to(self.record_dir).as_posix()
        self.extract_text_from_audio(rel_path)
        
        # 2. 추출이 모두 완료된 후 최종 파일명 입력받기
        try:
            custom_filename = input('\n저장할 파일명을 입력하세요 (엔터: 기본 날짜 형식 유지): ').strip()
        except KeyboardInterrupt:
            print('\n[알림] 입력이 취소되어 기본 파일명으로 유지합니다.')
            custom_filename = ''
            
        if custom_filename:
            if custom_filename.endswith('.wav'):
                custom_filename = custom_filename[:-4]
                
            new_filepath = date_folder / f'{custom_filename}.wav'
            counter = 1
            while new_filepath.exists():
                new_filepath = date_folder / f'{custom_filename}_{counter}.wav'
                counter += 1
                
            # .wav 와 .csv 파일 이름 동시 변경
            filepath.rename(new_filepath)
            csv_filepath = filepath.with_suffix('.csv')
            if csv_filepath.exists():
                csv_filepath.rename(new_filepath.with_suffix('.csv'))
                
            print(f'최종 파일이 저장되었습니다: {new_filepath}')
        else:
            print(f'최종 파일이 저장되었습니다: {filepath}')

    def play_audio(self, filename: str) -> None:
        """저장된 음성 파일을 재생합니다."""
        filepath = self.record_dir / filename
        if not filepath.exists():
            print('해당 파일을 찾을 수 없습니다.')
            return
            
        # WAV 파일의 기본 헤더 크기(44바이트)와 같거나 작으면 실제 오디오 데이터가 없는 것입니다.
        if filepath.stat().st_size <= 44:
            print('\n[오류] 실제 음성 데이터가 없는 빈 파일입니다. 마이크 권한이나 녹음 시간을 확인해 주세요.')
            return
            
        audio = pyaudio.PyAudio()
        try:
            with wave.open(str(filepath), 'rb') as wf:
                stream = audio.open(
                    format=audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                print(f'{filename} 재생을 시작합니다... (중간에 종료하려면 "q" 키를 누르세요)')
                data = wf.readframes(self.chunk)
                
                try:
                    while data:
                        stream.write(data)
                        data = wf.readframes(self.chunk)
                        
                        if msvcrt and msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key.lower() == b'q':
                                while msvcrt.kbhit(): msvcrt.getch()  # 버퍼 비우기
                                print('\n[재생 중단] 사용자의 요청으로 재생이 조기 종료되었습니다.')
                                break
                except KeyboardInterrupt:
                    print('\n[재생 강제 중단] Ctrl+C 입력이 감지되어 재생을 안전하게 중단합니다.')
                    
                print('\n재생이 완료되었습니다.')
                
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
        except Exception as e:
            print(f'재생 중 오류가 발생했습니다: {e}')
        finally:
            audio.terminate()

    def delete_audio(self, filename: str) -> None:
        """저장된 음성 파일을 삭제합니다."""
        filepath = self.record_dir / filename
        if not filepath.exists():
            print('해당 파일을 찾을 수 없습니다.')
            return
            
        try:
            filepath.unlink()
            print(f'{filename} 파일이 삭제되었습니다.')
        except OSError as e:
            print(f'파일 삭제 중 오류가 발생했습니다: {e}')

    def extract_text_from_audio(self, filename: str) -> None:
        """선택한 오디오 파일에서 STT를 수행하고 결과를 CSV로 저장합니다."""
        filepath = self.record_dir / filename
        if not filepath.exists():
            print('해당 파일을 찾을 수 없습니다.')
            return
            
        csv_filepath = filepath.with_suffix('.csv')
            
        recognizer = speech_recognition.Recognizer()
        
        print(f"'{filename}' 파일의 텍스트 추출을 시작합니다. (멀티스레드 고속 추출 중...)")
        
        try:
            audio_chunks = []
            with speech_recognition.AudioFile(str(filepath)) as source:
                audio_duration = source.DURATION
                
                chunk_duration = 10  # 10초 단위로 끊어서 메모리에 적재
                current_time = 0
                
                while current_time < audio_duration:
                    audio_data = recognizer.record(source, duration=chunk_duration)
                    start_time = self._format_seconds(current_time)
                    end_time = self._format_seconds(min(current_time + chunk_duration, audio_duration))
                    time_str = f'{start_time} ~ {end_time}'
                    audio_chunks.append((time_str, audio_data))
                    current_time += chunk_duration

            def process_chunk(chunk_info):
                t_str, a_data = chunk_info
                try:
                    txt = recognizer.recognize_google(a_data, language='ko-KR')
                except speech_recognition.UnknownValueError:
                    txt = '(음성 인식 불가)'
                except speech_recognition.RequestError as e:
                    txt = f'(API 오류: {e})'
                return t_str, txt

            results = []
            # ThreadPoolExecutor를 사용해 네트워크 I/O 병목 해소 (동시 API 요청)
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # map은 완료 순서와 상관없이 원래 전달된 오디오 조각의 순서를 유지해줍니다.
                for time_str, text in executor.map(process_chunk, audio_chunks):
                    results.append((time_str, text))
                    print(f'[{time_str}] {text}')

            with open(csv_filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['시간', '인식된 텍스트'])
                for row in results:
                    writer.writerow(row)
                    
            print(f'\nSTT 추출이 완료되었습니다. 결과가 저장되었습니다: {csv_filepath}')
        except Exception as e:
            print(f'STT 처리 중 오류가 발생했습니다: {e}')

    def _format_seconds(self, seconds: float) -> str:
        """초 단위의 시간을 MM:SS 형식의 문자열로 변환합니다."""
        m, s = divmod(int(seconds), 60)
        return f'{m:02d}:{s:02d}'

    def search_keyword_in_csv(self) -> None:
        """저장된 모든 CSV 파일에서 특정 키워드를 검색하여 출력합니다."""
        keyword = input('검색할 키워드를 입력하세요: ').strip()
        if not keyword:
            print('키워드가 입력되지 않았습니다.')
            return
            
        csv_files = list(self.record_dir.rglob('*.csv'))
        if not csv_files:
            print('저장된 STT 결과(CSV) 파일이 없습니다.')
            return
            
        print(f"\n--- '{keyword}' 검색 결과 ---")
        found = False
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for row in reader:
                        if len(row) >= 2:
                            time_str = row[0]
                            text = row[1]
                            if keyword in text:
                                rel_path = csv_file.relative_to(self.record_dir).as_posix()
                                print(f'[{rel_path}] {time_str} : {text}')
                                found = True
            except Exception:
                pass
                
        if not found:
            print('검색된 결과가 없습니다.')

    def _get_all_wav_files(self) -> List[str]:
        """내부 헬퍼: records 폴더 내의 모든 wav 파일 상대 경로 반환"""
        # rglob('*.wav')를 사용하면 os.walk보다 훨씬 직관적이고 빠르게 모든 하위 폴더의 wav 파일을 탐색합니다.
        return [p.relative_to(self.record_dir).as_posix() for p in self.record_dir.rglob('*.wav')]

    def _extract_date(self, rel_path: str) -> Optional[datetime]:
        """내부 헬퍼: 파일명, 폴더 경로, 메타데이터 순으로 생성 날짜를 유추합니다."""
        path_obj = Path(rel_path)
        filename = path_obj.name
        
        date_part = filename.split('-')[0]
        if len(date_part) == 8 and date_part.isdigit():
            try:
                return datetime.strptime(date_part, '%Y%m%d')
            except ValueError:
                pass
                
        parts = path_obj.parent.parts
        if len(parts) >= 3:
            try:
                return datetime.strptime(''.join(parts[-3:]), '%Y%m%d')
            except ValueError:
                pass
                
        try:
            full_path = self.record_dir / rel_path
            mtime = full_path.stat().st_mtime
            return datetime.fromtimestamp(mtime).replace(hour=0, minute=0, second=0, microsecond=0)
        except OSError:
            return None

    def show_records_in_range(self, start_date_str: str, end_date_str: str) -> List[str]:
        """보너스 기능: 특정 범위의 날짜에 저장된 녹음 파일을 보여줍니다."""
        if not self.record_dir.exists():
            print('녹음 폴더가 아직 존재하지 않습니다.')
            return []

        try:
            start_date = datetime.strptime(start_date_str, '%Y%m%d')
            end_date = datetime.strptime(end_date_str, '%Y%m%d')
        except ValueError:
            print('잘못된 날짜 형식입니다. YYYYMMDD 형식으로 입력해주세요.')
            return []

        print(f'\n--- {start_date_str} 부터 {end_date_str} 까지의 녹음 파일 ---')
        matched_files = []
        
        for rel_path in self._get_all_wav_files():
            file_date = self._extract_date(rel_path)
            if file_date and start_date <= file_date <= end_date:
                matched_files.append(rel_path)
                
        if not matched_files:
            print('해당 기간에 녹음된 파일이 없습니다.')
        else:
            for idx, file in enumerate(matched_files, 1):
                print(f'{idx}. {file}')
                
        return matched_files

    def list_all_records(self) -> List[str]:
        """전체 녹음 파일 목록을 화면에 보여주고 리스트로 반환합니다."""
        if not self.record_dir.exists():
            print('녹음 폴더가 아직 존재하지 않습니다.')
            return []
            
        files = self._get_all_wav_files()
        if not files:
            print('녹음된 파일이 없습니다.')
            return []
            
        print('\n--- 전체 녹음 파일 목록 ---')
        for idx, file in enumerate(files, 1):
            print(f'{idx}. {file}')
            
        return files


def select_file_index(files: List[str], action_name: str) -> Optional[str]:
        """파일 리스트에서 사용자 입력을 받아 유효한 파일명을 반환합니다."""
        if not files:
            return None
            
        choice = input(f'{action_name} 파일의 번호를 입력하세요 (취소: 엔터): ')
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(files):
                return files[idx - 1]
            print('잘못된 번호입니다.')
        return None

def main() -> None:
    """J.A.V.I.S 메인 시스템 실행 함수"""
    recorder = AudioRecorder()
    
    while True:
        print('\n[ J.A.V.I.S 음성 기록 시스템 ]')
        print('1. 음성 녹음 시작')
        print('2. 녹음 파일 조회 (전체/기간)')
        print('3. 녹음 파일 재생')
        print('4. 녹음 파일 삭제')
        print('5. STT 키워드 검색')
        print('6. 시스템 종료')
        
        choice = input('원하시는 메뉴 번호를 입력하세요: ')
        
        if choice == '1':
            recorder.record_audio()
        elif choice == '2':
            start = input('검색 시작 날짜 입력 (예: 20260520, 전체 조회는 엔터): ').strip()
            if not start:
                matched_files = recorder.list_all_records()
            else:
                end = input('검색 종료 날짜 입력 (예: 20260522): ').strip()
                matched_files = recorder.show_records_in_range(start, end)
                
            target = select_file_index(matched_files, '재생할')
            if target:
                recorder.play_audio(target)
        elif choice == '3':
            all_files = recorder.list_all_records()
            target = select_file_index(all_files, '재생할')
            if target:
                recorder.play_audio(target)
        elif choice == '4':
            all_files = recorder.list_all_records()
            target = select_file_index(all_files, '삭제할')
            if target:
                confirm = input(f"'{target}' 파일을 정말 삭제하시겠습니까? (y/n): ")
                if confirm.lower() == 'y':
                    recorder.delete_audio(target)
                else:
                    print('삭제가 취소되었습니다.')
        elif choice == '5':
            recorder.search_keyword_in_csv()
        elif choice == '6':
            print('J.A.V.I.S 시스템을 종료합니다.')
            break
        else:
            print('올바른 번호를 입력해주세요.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n[시스템 종료] Ctrl+C 입력으로 인해 J.A.V.I.S 시스템을 안전하게 종료합니다.')