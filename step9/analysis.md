# v4 하이브리드 점수 모델 - 기술 검토

이 문서는 `step9` 카이사르 암호 해독기의 **심층 기술 검토 및 점수 모델 분석** 문서입니다.  
세부 구현과 점수 계산 로직, N-gram/감점 전략 등을 중심으로 설명합니다.

> 개요 및 제출용 내용은 `overview.md`를 참고하세요.

---

## 1. 구현 핵심

### 1.1 N-gram 분석

- `COMMON_BIGRAMS`와 `COMMON_TRIGRAMS`를 사용해 자연스러운 영어 조합에 가산점을 부여합니다.
- 빅람 예시: `th`, `he`, `in`, `er`, `an`
- 트라이그램 예시: `the`, `and`, `ing`, `her`, `hat`

```python
COMMON_BIGRAMS = {
    'th': 15, 'he': 12, 'in': 10, 'er': 9, 'an': 8, 're': 7, 'es': 7, 'on': 6,
    'st': 6, 'nt': 6, 'en': 6, 'at': 6, 'ed': 5, 'nd': 5, 'to': 5, 'or': 5,
    'ea': 5, 'ti': 5, 'ar': 5, 'te': 5, 'ng': 5, 'al': 4, 'it': 4, 'as': 4,
    'is': 4, 'ha': 4, 'et': 4, 'se': 4, 'ou': 4, 'hi': 4, 'le': 4, 've': 4,
    'co': 4, 'me': 4, 'de': 4, 'ri': 4, 'ro': 4, 'ic': 4, 'ne': 4, 'ma': 4
}

COMMON_TRIGRAMS = {
    'the': 25, 'and': 15, 'ing': 12, 'her': 8, 'hat': 7, 'his': 7, 'tha': 6,
    'ere': 6, 'for': 6, 'ent': 6, 'ion': 6, 'ter': 5, 'was': 5, 'you': 5,
    'ith': 5, 'ver': 5, 'all': 5, 'wit': 5, 'thi': 5, 'tio': 4, 'eve': 4,
    'rea': 4, 'com': 4, 'par': 4, 'con': 4, 'men': 4, 'est': 4, 'sta': 4,
    'lar': 4, 'but': 4, 'can': 4, 'had': 4, 'by': 4, 'not': 4, 'one': 4
}
```

**효과:**
- 영어 문장은 연속된 문자 패턴이 많으므로, 해당 패턴 점수로 자연스러운 후보를 선별할 수 있습니다.
- 예시: `I love Mars`에서 `lo`, `ve`, `ma`, `rs`가 모두 긍정적 신호가 됩니다.

---

### 1.2 금지 조합 감점

- `FORBIDDEN_BIGRAMS`에 포함된 희귀 조합은 점수를 크게 깎습니다.
- 추가로 `qq`, `vv`, `ww`, `xx`, `yy`, `zz` 같은 반복 글자 패턴도 감점합니다.

```python
FORBIDDEN_BIGRAMS = {
    'jq', 'jz', 'qj', 'qz', 'vj', 'vq', 'vx', 'wx', 'xj', 'zx',
    'bz', 'cz', 'dz', 'fz', 'gz', 'hz', 'jz', 'kz', 'lz', 'mz', 'nz', 'pz', 'rz', 'tz', 'vz', 'wz', 'xz', 'zz'
}
```

**효과:**
- 비영어 후보 중에서 높은 점수를 받을 수 있는 잘못된 조합을 제거합니다.
- 예시: `D gjqz Hvmn`은 `qz`, `gj` 등으로 인해 큰 감점을 받습니다.

---

### 1.3 사전 + 통계 하이브리드 점수

- `dictionary.txt` 기반 단어 발견 시 기본 점수와 추가 보너스를 부여합니다.
- 통계적 점수(N-gram, 모음 비율, 단어 개수)와 결합해 최종 점수를 계산합니다.

```python
base_dict_score = len(valid_words) * 20
bonus_dict_score = len(valid_words) * 10
```

**효과:**
- 단어가 포함된 후보에 신뢰도를 높이는 보너스 효과를 줍니다.
- 사전 기반 정보가 없어도 통계 점수만으로 비교가 가능하도록 설계되어 있습니다.

---

## 2. 점수 구조

최종 점수는 다음 요소의 합으로 계산됩니다.

- 사전 단어 기본 점수
- 사전 단어 보너스 점수
- 일반 단어 점수
- 단어 길이 점수
- 모음 비율 점수
- 단어 개수 점수
- N-gram 점수
- 금지 조합 감점

```python
total_score = (dict_base + dict_bonus + common_words_score + word_length +
               vowel_score + word_count_score + ngram_score - penalty_score)
```

---

## 3. 대표 사례: `I love Mars`

### 점수 구성

```
사전 기본: 40점 (love:20, mars:20)
사전 보너스: 20점 (각 단어당 +10)
일반 단어: 45점 (love:15, mars:15, i:15)
단어 길이: 8점 (love:4, mars:4)
모음 비율: 30점 (적절한 44% 비율)
단어 개수: 10점 (3단어 → 10점)
N-gram: 13점 (lo:4, ve:4, ma:4, rs:1)
감점: 0점
총합: 166점
```

이 결과는 같은 암호문에서 다른 후보보다 월등히 높은 점수를 받았습니다.

---

## 4. 기술 검토 핵심

### 4.1 중복 없이 분리된 설정

- `config.py`에 점수 기준과 가중치를 둬서 정책 변경이 쉽습니다.
- `ngrams.py`에 패턴 데이터를 분리해 로직과 데이터를 분리했습니다.

### 4.2 평가 기준 일치

- `target_text` 파라미터를 사용한 `caesar_cipher_decode()`를 유지합니다.
- 모든 shift를 시도하고 결과를 출력합니다.
- 예외 처리가 적용된 파일 입출력으로 안전성을 보장합니다.
- 최고점 결과를 `result.txt`에 저장합니다.