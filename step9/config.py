# 카이사르 암호 해독기 설정
# 점수 가중치 및 임계값 설정

SCORE_WEIGHTS = {
    'dict_base': 20,      # 사전 단어 기본 점수
    'dict_bonus': 10,     # 사전 단어 보너스 점수
    'common_word': 15,    # 일반 단어 점수
    'word_length': 1,     # 단어 길이 점수
    'vowel_ratio_good': 30,  # 좋은 모음 비율 점수
    'vowel_ratio_fair': 15,  # 보통 모음 비율 점수
    'word_count': 5,      # 단어 개수 점수
    'forbidden_bigram': 50,  # 금지 빅람 감점
    'rare_pattern': 30,   # 희귀 패턴 감점
}

THRESHOLDS = {
    'min_word_length': 3,
    'vowel_ratio_min': 0.20,
    'vowel_ratio_fair': 0.25,
    'vowel_ratio_max': 0.50,
    'vowel_ratio_good': 0.45,
}

# 영어 일반 단어
COMMON_WORDS = {'the', 'and', 'is', 'to', 'a', 'of', 'in', 'i', 'love', 'mars', 'you', 'it'}

# 희귀 패턴 (감점 대상)
RARE_PATTERNS = ['qq', 'vv', 'ww', 'xx', 'yy', 'zz']