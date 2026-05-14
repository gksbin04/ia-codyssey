# 카이사르 암호 해독기 개요

## 1. 문서 목적

이 문서는 `step9` 카이사르 암호 해독기의 **제출용 개요 문서**입니다.  
구현 구조, 요구사항 충족 여부, 실행 결과를 간결하게 정리했습니다.

> 자세한 점수 모델 분석과 기술 검토는 `analysis.md`를 참고하세요.

---

## 2. 프로젝트 구성

```
Mars_mission/step9/
├── main.py          # 메인 프로그램
├── dictionary.txt   # 사전 단어 목록
├── password.txt     # 암호문 파일
├── result.txt       # 해독 결과 저장 파일
├── config.py        # 점수 가중치와 기준 설정
└── ngrams.py        # N-gram 및 금지 조합 데이터
```

---

## 3. 구현 개요

- `password.txt`에서 암호문을 읽음
- `caesar_cipher_decode(target_text, shift)`로 1~26 shift 해독
- 각 후보 결과에 점수를 매겨 가장 영어에 가까운 결과를 선택
- `result.txt`에 최종 해독 결과 저장
- 파일 입출력은 예외 처리로 안전하게 구현

이 구현은 요구사항을 모두 만족하며, 추가로 **N-gram 분석, 금지 조합 감점, 사전 기반 하이브리드 점수**를 적용했습니다.

---

## 4. 요구사항 충족 여부

- `password.txt` 파일 읽기: ✅
- `caesar_cipher_decode()` 함수 구현: ✅
- 함수 인수 이름 `target_text`: ✅
- 1~26 shift 반복 출력: ✅
- `result.txt` 저장: ✅
- 파일 입출력 예외 처리: ✅
- 사전 단어 탐지로 자동 반복 중단(보너스): ✅

---

## 5. 주요 결과

```
암호문: B ehox Ftkl
```

| shift | 결과 |
|------:|------|
| 1 | A dgnw Esjk |
| 7 | U xahq Ymde |
| 19 | **I love Mars** |
| 26 | B ehox Ftkl |

**정답: shift 19 → `I love Mars`**

---

## 6. 코드 구조 요약

- `main.py`: 전체 실행 흐름과 최고 점수 후보 선택
- `config.py`: 점수 가중치 및 평가 기준 설정
- `ngrams.py`: N-gram 및 금지 조합 데이터 저장

---

## 7. 요약

이 문서는 제출용 개요로서 구현 목적, 요구사항 충족, 주요 결과를 간결히 정리했습니다.  
세부 점수 모델, 평가 기준, 기술 분석 등은 `v4_analysis.md`에 정리되어 있습니다.
