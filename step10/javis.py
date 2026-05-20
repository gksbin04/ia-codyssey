import wave
import struct
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
        
        try:
            custom_filename = input('저장할 파일명을 입력하세요 (엔터: 기본 날짜 형식): ').strip()
        except KeyboardInterrupt:
            print('\n[알림] 입력이 취소되어 기본 파일명으로 안전하게 자동 저장합니다.')
            custom_filename = ''

        now = datetime.now()
        if custom_filename:
            base_filename = custom_filename
            if base_filename.endswith('.wav'):
                base_filename = base_filename[:-4]
        else:
            # 파일 이름 포맷: 년월일-시간분초
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
            
        print(f'파일이 저장되었습니다: {filepath}')

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
        print('5. 시스템 종료')
        
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
            print('J.A.V.I.S 시스템을 종료합니다.')
            break
        else:
            print('올바른 번호를 입력해주세요.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n[시스템 종료] Ctrl+C 입력으로 인해 J.A.V.I.S 시스템을 안전하게 종료합니다.')