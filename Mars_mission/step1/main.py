LOG_FILE = 'mission_computer_main.log'
REVERSE_FILE = 'mission_computer_reverse.log'
PROBLEM_FILE = 'mission_computer_main_problem.log'
REPORT_FILE = 'log_analysis.md'

INCLUDE_KEYWORDS = [
    'unstable', 'explosion',  # 직접 현상
    'pressure', 'overpressure', 'high pressure',  # 압력 이상
    'temp', 'temperature', 'overheat', 'fire',    # 온도 이상
    'leak', 'leakage', 'rupture',                 # 구조적 결함
    'voltage', 'short', 'battery', 'power',       # 전압/전력 문제
    'warning', 'critical', 'error', 'failed'      # 시스템 경고
]

EXCLUDE_KEYWORDS = [
    'online', 'optimal', 'nominal', 'stable',
    'success', 'complete', 'checked', 'passed'
]


def print_hello():
    print('Hello Mars')


def read_log_file(file_name):
    lines = []
    with open(file_name, 'r', encoding = 'utf-8') as file:
        while True:
            line = file.readline()
            if not line:
                break
            lines.append(line)
    return lines


def print_log(lines):
    print('===== mission_computer_main.log 전체 내용 =====')
    for line in lines:
        print(line, end = '')
    print('\n===== 출력 종료 =====')


def sort_log_data(log_data):
    header_lines = []
    body_lines = []
    for line in log_data:
        extracted_timestamp = line[:19]
        clean_timestamp = extracted_timestamp.replace('-', '').replace(':', '').replace(' ', '').strip()
        if clean_timestamp.isdigit() and len(clean_timestamp) > 0:
            body_lines.append(line)
        else:
            header_lines.append(line)
    sorted_body = sorted(body_lines, reverse = True)
    return header_lines + sorted_body


def add_line_numbers(log_data):
    numbered_logs = []
    for index, line in enumerate(log_data):
        line_number = index + 1
        numbered_line = f'[Line {line_number}] {line}'
        numbered_logs.append(numbered_line)
    return numbered_logs


def extract_problem_logs(log_data):
    problem_logs = []
    for line in log_data:
        clean_line = line.lower().replace(',', ' ').replace('.', ' ')
        words_in_line = clean_line.split()
        include_hit = False
        for word in INCLUDE_KEYWORDS:
            if word in words_in_line:
                include_hit = True
                break
        if include_hit:
            exclude_hit = False
            for word in EXCLUDE_KEYWORDS:
                if word in words_in_line:
                    exclude_hit = True
                    break
            if not exclude_hit:
                problem_logs.append(line)
    return problem_logs


def save_log_to_file(file_path, data):
    with open(file_path, 'w', encoding = 'utf-8') as f:
        for line in data:
            f.write(line)


def get_context_lines(lines, line_number, window_size = 1):
    start_index = max(0, line_number - window_size - 1)
    end_index = min(len(lines), line_number + window_size)

    context_entries = []
    for index in range(start_index, end_index):
        context_entries.append((index + 1, lines[index].rstrip('\n')))
    return context_entries


def write_report(file_name, lines, problem_data):
    """
    한빈 님의 피드백을 반영하여 추측성 문구를 제거하고 
    로그 기반의 사실로만 보고서를 작성합니다.
    """
    report_lines = []

    report_lines.append('# 🚀 사고 분석 보고서 (Log Analysis Report)\n\n')
    report_lines.append('## 1. 개요\n')
    report_lines.append('* **분석 대상:** 화성 탐사선 메인 미션 컴퓨터 로그 (`mission_computer_main.log`)\n')
    report_lines.append('* **사고 시각:** 2023-08-27 11:40:00\n')
    report_lines.append('* **목적:** 추출된 특이 로그 및 주변 맥락을 분석하여 시스템 종료의 결정적 원인을 규명함.\n\n')

    report_lines.append('## 2. 분석 방법\n')
    report_lines.append('* **필터링 알고리즘:** \'unstable\', \'explosion\' 등 사고 핵심 키워드 및 \'pressure\' 등 수치 변화 관련 로그 추출.\n')
    report_lines.append('* **맥락 분석:** 특정 오류 로그 발생 시점의 앞뒤 로그를 함께 검토하여 정상 작동 여부와 대조 분석함.\n')
    report_lines.append('* **위치 식별:** `add_line_numbers` 함수를 통해 원본 로그의 행 번호를 명시하여 데이터의 객관성 확보.\n\n')

    report_lines.append('## 3. 사고 원인 추정\n')
    report_lines.append('* **잠재적 위험 구간 검토 (Line 16):** 10:35:00 부근에서 최대 동압(max-Q)에 따른 압력 증가가 관측됨. 그러나 주변 로그(`Line 15`, `Line 17`) 확인 결과, 시스템은 구조적 건전성을 확인하며 정상적으로 해당 구간을 통과한 것으로 분석됨.\n')
    report_lines.append('* **돌발적 상태 전이 (Line 34):** 11:30:00까지 모든 시스템이 정상(`nominal`)이었으나, 11:35:00에 이르러 알 수 없는 이유로 산소 탱크가 급격히 `unstable` 상태로 전환됨.\n')
    report_lines.append('* **물리적 파손 (Line 35):** 불안정 상태 감지 5분 후인 11:40:00에 탱크가 최종 폭발하며 시스템 전체가 셧다운됨.\n\n')

    report_lines.append('## 4. 문제 의심 로그와 위치 (상세 맥락)\n')
    report_lines.append('사고와 직결된 로그 및 원인 파악을 위해 검토된 주변 로그의 상세 내용입니다.\n\n')
    report_lines.append('| 위치 (Line) | 발생 시각 | 상태 | 로그 내용 (Log Message) | 분석 의견 |\n')
    report_lines.append('| :--- | :--- | :--- | :--- | :--- |\n')
    report_lines.append('| 15 | 10:30:00 | INFO | Main engine throttle at 100%. | 정상 가속 중 |\n')
    report_lines.append('| **16** | **10:35:00** | **INFO** | **Approaching max-Q. Aerodynamic pressure increasing.** | **[검토] 이상 없음** |\n')
    report_lines.append('| 17 | 10:40:00 | INFO | Max-Q passed. Structural integrity confirmed. | 구조적 안전 확인 |\n')
    report_lines.append('| ... | ... | ... | ... | ... |\n')
    report_lines.append('| 33 | 11:30:00 | INFO | All systems nominal. Oxygen flow steady. | 사고 5분 전 정상 |\n')
    report_lines.append('| **34** | **11:35:00** | **WARNING** | **Oxygen tank unstable.** | **[주의] 이상 징후 발생** |\n')
    report_lines.append('| **35** | **11:40:00** | **CRITICAL** | **Oxygen tank explosion.** | **[사고] 최종 폭발 지점** |\n')
    report_lines.append('| 36 | 12:00:00 | INFO | Center and mission control systems powered down. | 시스템 강제 종료 |\n\n')

    report_lines.append('## 5. 분석 결과\n')
    report_lines.append('* **정상 구간 식별:** 발사 초기의 압력 증가 구간(`Line 16`)은 로그상 \'Structural integrity confirmed\'와 연결되어 사고의 직접적 원인에서 제외됨.\n')
    report_lines.append('* **급격한 상태 변화:** 사고는 11:30(`Line 33`)의 정상 상태에서 11:35(`Line 34`)의 불안정 상태로 매우 급격하게 전개됨.\n')
    report_lines.append('* **인과관계:** `Line 34`의 경고 발생 후 5분 만에 물리적 폭발(`Line 35`)로 이어짐.\n\n')

    report_lines.append('## 6. 결론\n')
    report_lines.append('본 사고의 직접적인 원인은 **11시 40분에 발생한 산소 탱크의 물리적 폭발**임. 분석 결과, 발사 과정의 압력 증가는 성공적으로 견뎌냈으나, 이후 알 수 없는 이유로 발생한 11시 35분의 시스템 불안정 상태가 제어 불능 상태에 빠지며 최종 폭발로 이어진 것으로 결론지음.\n\n')

    with open(file_name, 'w', encoding = 'utf-8') as file:
        for line in report_lines:
            file.write(line)


if __name__ == '__main__':
    print_hello()
    try:
        log_lines = read_log_file(LOG_FILE)
        print_log(log_lines)

        reverse_lines = sort_log_data(log_lines)
        save_log_to_file(REVERSE_FILE, reverse_lines)
        print_log(reverse_lines)

        numbered_content = add_line_numbers(log_lines)
        problem_data = extract_problem_logs(numbered_content)
        save_log_to_file(PROBLEM_FILE, problem_data)

        write_report(REPORT_FILE, log_lines, problem_data)

    except FileNotFoundError:
        print('에러: 파일을 찾을 수 없습니다.' + LOG_FILE)
    except PermissionError:
        print('에러: 파일 접근 권한이 없습니다.')
    except UnicodeDecodeError:
        print('로그 파일 인코딩이 UTF-8이 아닙니다.')
    except Exception as error:
        print('알 수 없는 오류가 발생했습니다:' + str(error))