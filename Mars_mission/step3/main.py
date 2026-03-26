INVENTORY_FILE_PATH = 'Mars_Base_Inventory_List.csv'
BINARY_FILE_PATH = 'Mars_Base_Inventory_List.bin'
DANGER_FILE_PATH = 'Mars_Base_Inventory_danger.csv'


def parse_line(line):
    row = []
    current = ''
    in_quotes = False
    
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
            continue
        elif char == ',' and not in_quotes:
            row.append(current.strip())
            current = ''
        else:
            current += char
    
    row.append(current.strip())
    return row


def read_csv(file_path):
    inventory_list = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            header_line = next(f).strip()
            header = parse_line(header_line)

            try:
                flammability_idx = header.index('Flammability')
            except ValueError:
                raise ValueError('Flammability 컬럼이 존재하지 않습니다.')
            
            for line in f:
                clean_line = line.strip()
                if not clean_line:
                    continue
                    
                row = parse_line(clean_line)
                
                try:
                    row[flammability_idx] = float(row[flammability_idx])
                except (ValueError, IndexError):
                    row[flammability_idx] = 0.0

                inventory_list.append(row)
                    
        return header, inventory_list, flammability_idx

    except FileNotFoundError:
        print(f'파일 없음: {file_path}')
    except PermissionError:
        print(f'권한 오류: {file_path}')
    except IOError:
        print(f'입출력 오류 발생: {file_path}')
    
    # 에러 발생 시 main에서 언패킹 에러가 나지 않도록 빈 값 반환
    return [], [], -1


def print_list(header, inventory_list):
    print(f'Header: {header}')
    print('-' * 50)
    for item in inventory_list:
        print(item)


def sort_by_flammability(inventory_list, flam_idx):
    if flam_idx != -1:
        inventory_list.sort(
            key=lambda row: row[flam_idx],
            reverse=True
        )


def filter_danger_items(inventory_list, flam_idx):
    danger_list = []
    if flam_idx == -1:
        return danger_list
        
    for row in inventory_list:
        if row[flam_idx] >= 0.7:
            danger_list.append(row)
    return danger_list


def save_as_csv(file_path, header, data_list):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(','.join(header) + '\n')
            
            for row in data_list:
                str_row = []
                for item in row:
                    text = str(item)
                    if ',' in text:
                        text = f'"{text}"'
                    str_row.append(text)
                
                f.write(','.join(str_row) + '\n')

    except PermissionError:
        print(f'파일 쓰기 권한 없음: {file_path}')
    except IOError:
        print(f'CSV 저장 중 입출력 오류 발생: {file_path}')


def save_as_binary(file_path, header, inventory_list):
    try:
        with open(file_path, 'wb') as f:
            for row in inventory_list:
                if len(header) != len(row):
                    print(f'경고: 길이 불일치 → {row}')
                    continue

                parts = []
                for k, v in zip(header, row):
                    parts.append(f'{k}={v}')

                line = '|'.join(parts)
                f.write(line.encode('utf-8') + b'\n')

    except PermissionError:
        print(f'파일 쓰기 권한 없음: {file_path}')
    except IOError:
        print(f'이진 파일 저장 중 입출력 오류 발생: {file_path}')


def read_binary(file_path):
    inventory_list = []
    header = []

    try:
        with open(file_path, 'rb') as f:
            for line in f:
                decoded_line = line.decode('utf-8').strip()
                if not decoded_line:
                    continue
                
                pairs = decoded_line.split('|')
                row = []

                if not header:
                    for item in pairs:
                        key, _ = item.split('=', 1)
                        header.append(key)

                for item in pairs:
                    _, value = item.split('=', 1)
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                    row.append(value)
                
                inventory_list.append(row)

    except FileNotFoundError:
        print(f'파일 없음: {file_path}')
    except PermissionError:
        print(f'파일 읽기 권한 없음: {file_path}')
    except IOError:
        print(f'이진 파일 읽기 중 입출력 오류 발생: {file_path}')

    return header, inventory_list


def main():
    try:
        header, inventory_data, flam_idx = read_csv(INVENTORY_FILE_PATH)
        if not header:
            return

        print('CSV 파일에서 읽은 데이터:')
        print_list(header, inventory_data)
        sort_by_flammability(inventory_data, flam_idx)
        save_as_binary(BINARY_FILE_PATH, header, inventory_data)
        
        print('\n이진 파일 읽어서 출력:')
        new_header, new_data = read_binary(BINARY_FILE_PATH)
        print_list(new_header, new_data)

        danger_list = filter_danger_items(inventory_data, flam_idx)
        print('\n위험 물질 데이터:')
        print_list(header, danger_list)

        save_as_csv(DANGER_FILE_PATH, header, danger_list)

        header_d, inventory_d, flam_idx_d = read_csv(DANGER_FILE_PATH)
        print('\nDANGER_FILE_PATH에서 읽는 위험물질 데이터:')
        print_list(header_d, inventory_d)

    except Exception as e:
        print(f'프로그램 실행 중 예외 발생: {e}')


if __name__ == '__main__':
    main()