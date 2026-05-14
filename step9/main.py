"""
고급 카이사르 암호 해독기
N-gram 분석, 감점 시스템, 하이브리드 가중치를 활용한 자동 해독
"""

import os
from typing import Dict, List, Set, Tuple, Optional, Any
from config import SCORE_WEIGHTS, THRESHOLDS, COMMON_WORDS, RARE_PATTERNS
from ngrams import COMMON_BIGRAMS, COMMON_TRIGRAMS, FORBIDDEN_BIGRAMS


def get_file_path(filename: str) -> str:
    """현재 파일 기준 절대 경로를 반환한다."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, filename)


def load_dictionary(file_path: str) -> Set[str]:
    """사전 파일을 읽어 단어 집합을 반환한다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return {line.strip().lower() for line in file if line.strip()}
    except FileNotFoundError:
        print(f'경고: 사전 파일을 찾을 수 없습니다 - {file_path}')
        return set()
    except UnicodeDecodeError:
        print(f'경고: 파일 인코딩 오류 - {file_path}')
        return set()
    except Exception as e:
        print(f'오류: 사전 파일 읽기 실패 - {e}')
        return set()


def caesar_cipher_decode(target_text: str, shift: int) -> str:
    """카이사르 암호를 주어진 자리수로 해독한다."""
    result = []
    for char in target_text:
        if char.islower():
            decoded = chr((ord(char) - ord('a') - shift) % 26 + ord('a'))
            result.append(decoded)
        elif char.isupper():
            decoded = chr((ord(char) - ord('A') - shift) % 26 + ord('A'))
            result.append(decoded)
        else:
            result.append(char)
    return ''.join(result)


def calculate_ngram_score(text: str) -> int:
    """
    N-gram 분석으로 점수를 계산한다.
    빅람과 트라이그램의 빈도를 기반으로 영어스러운 정도를 평가.
    """
    score = 0
    text_lower = text.lower()

    # 빅람 분석 (2글자 조합)
    for i in range(len(text_lower) - 1):
        bigram = text_lower[i:i+2]
        if bigram in COMMON_BIGRAMS:
            score += COMMON_BIGRAMS[bigram]
        elif bigram in FORBIDDEN_BIGRAMS:
            score -= SCORE_WEIGHTS['forbidden_bigram']

    # 트라이그램 분석 (3글자 조합)
    for i in range(len(text_lower) - 2):
        trigram = text_lower[i:i+3]
        if trigram in COMMON_TRIGRAMS:
            score += COMMON_TRIGRAMS[trigram]

    return score


def calculate_penalty_score(text: str) -> int:
    """
    금지된 조합에 대한 감점 시스템.
    영어에서 매우 희귀하거나 불가능한 문자 조합이 있으면 점수를 깎는다.
    """
    penalty = 0
    text_lower = text.lower()

    # 금지된 빅람 감점
    for i in range(len(text_lower) - 1):
        bigram = text_lower[i:i+2]
        if bigram in FORBIDDEN_BIGRAMS:
            penalty += SCORE_WEIGHTS['forbidden_bigram']

    # 희귀 패턴 감점
    for pattern in RARE_PATTERNS:
        if pattern in text_lower:
            penalty += SCORE_WEIGHTS['rare_pattern']

    return penalty


def analyze_vowel_ratio(text: str) -> int:
    """모음 비율을 분석하여 점수를 반환한다."""
    vowels = sum(1 for c in text.lower() if c in 'aeiou')
    consonants = sum(1 for c in text.lower() if c.isalpha() and c not in 'aeiou')
    total = vowels + consonants

    if total == 0:
        return 0

    vowel_ratio = vowels / total

    if THRESHOLDS['vowel_ratio_fair'] <= vowel_ratio <= THRESHOLDS['vowel_ratio_good']:
        return SCORE_WEIGHTS['vowel_ratio_good']
    elif THRESHOLDS['vowel_ratio_min'] <= vowel_ratio <= THRESHOLDS['vowel_ratio_max']:
        return SCORE_WEIGHTS['vowel_ratio_fair']

    return 0


def calculate_dictionary_score(words: List[str], dictionary: Set[str]) -> Tuple[int, int, int]:
    """사전 기반 점수를 계산한다."""
    valid_words = [w for w in words if len(w) >= THRESHOLDS['min_word_length'] and w in dictionary]

    base_score = len(valid_words) * SCORE_WEIGHTS['dict_base']
    bonus_score = len(valid_words) * SCORE_WEIGHTS['dict_bonus']
    length_score = sum(len(w) for w in valid_words) * SCORE_WEIGHTS['word_length']

    return base_score, bonus_score, length_score


def calculate_common_words_score(words: List[str]) -> int:
    """일반 단어 포함 점수를 계산한다."""
    common_count = sum(1 for w in words if w in COMMON_WORDS)
    return common_count * SCORE_WEIGHTS['common_word']


def calculate_word_count_score(words: List[str]) -> int:
    """단어 개수 기반 점수를 계산한다."""
    if len(words) > 1:
        return (len(words) - 1) * SCORE_WEIGHTS['word_count']
    return 0


def calculate_hybrid_score(text: str, dictionary: Set[str]) -> Tuple[int, Dict[str, int]]:
    """
    사전 대조와 통계의 하이브리드 가중치 적용.
    사전에 있는 단어가 발견되면 보너스 점수를 부여하고,
    통계적 분석도 함께 수행한다.

    Returns:
        Tuple[int, Dict[str, int]]: (총점, 점수 분석)
    """
    words = text.lower().split()
    if not words:
        return 0, {}

    # 사전 기반 점수
    dict_base, dict_bonus, word_length = calculate_dictionary_score(words, dictionary)

    # 일반 단어 점수
    common_words_score = calculate_common_words_score(words)

    # 모음 비율 점수
    vowel_score = analyze_vowel_ratio(text)

    # 단어 개수 점수
    word_count_score = calculate_word_count_score(words)

    # N-gram 점수
    ngram_score = calculate_ngram_score(text)

    # 감점
    penalty_score = calculate_penalty_score(text)

    # 총점 계산
    total_score = (dict_base + dict_bonus + common_words_score + word_length +
                   vowel_score + word_count_score + ngram_score - penalty_score)

    # 점수 분석
    breakdown = {
        'dict_base': dict_base,
        'dict_bonus': dict_bonus,
        'common_words': common_words_score,
        'word_length': word_length,
        'vowel_ratio': vowel_score,
        'word_count': word_count_score,
        'ngram': ngram_score,
        'penalty': -penalty_score
    }

    return total_score, breakdown


def solve_mission_advanced() -> None:
    """고급 하이브리드 방식 카이사르 암호 해독을 수행한다."""
    password_path = get_file_path('password.txt')
    dictionary_path = get_file_path('dictionary.txt')
    result_path = get_file_path('result.txt')

    # 암호문 읽기
    try:
        with open(password_path, 'r', encoding='utf-8') as file:
            cipher_text = file.read().strip()
    except FileNotFoundError:
        print(f'오류: 암호 파일을 찾을 수 없습니다 - {password_path}')
        return
    except Exception as e:
        print(f'오류: 암호 파일 읽기 실패 - {e}')
        return

    # 사전 로드
    dictionary = load_dictionary(dictionary_path)

    print(f'--- 고급 하이브리드 방식 암호 해독: {cipher_text} ---\n')

    results = []

    # 모든 shift에 대해 점수 계산
    for shift in range(1, 27):
        decoded = caesar_cipher_decode(cipher_text, shift)
        score, breakdown = calculate_hybrid_score(decoded, dictionary)

        results.append({
            'shift': shift,
            'text': decoded,
            'score': score,
            'breakdown': breakdown
        })

        print(f'Shift {shift:2d}: {decoded:20s} | 점수: {score:4d}')

    # 최고 점수의 결과 선택
    best_result = max(results, key=lambda x: x['score'])
    final_result = best_result['text']

    print(f'\n🏆 최고 점수: Shift {best_result["shift"]} - "{final_result}" (점수: {best_result["score"]})')

    # 상세 점수 분석 출력
    print('\n📊 점수 분석:')
    breakdown = best_result['breakdown']
    print(f'  사전 기본: {breakdown["dict_base"]:3d}점')
    print(f'  사전 보너스: {breakdown["dict_bonus"]:3d}점')
    print(f'  일반 단어: {breakdown["common_words"]:3d}점')
    print(f'  단어 길이: {breakdown["word_length"]:3d}점')
    print(f'  모음 비율: {breakdown["vowel_ratio"]:3d}점')
    print(f'  단어 개수: {breakdown["word_count"]:3d}점')
    print(f'  N-gram: {breakdown["ngram"]:3d}점')
    print(f'  감점: {breakdown["penalty"]:3d}점')

    # 결과 저장
    try:
        with open(result_path, 'w', encoding='utf-8') as file:
            file.write(final_result)
        print(f'\n결과가 저장되었습니다: {result_path}')
    except Exception as e:
        print(f'결과 저장 중 오류 발생: {e}')


if __name__ == '__main__':
    solve_mission_advanced()
