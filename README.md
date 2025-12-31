# pwnable-lab
포너블 공부 기록 모음집

※ 가상머신에서만 사용할 것을 추천.

---

## 구성

예시, 변동 있음.

```
pwnable-lab/
├── setup.sh            // 패키지, 툴, 32bit 환경 설정
├── stack-bof-basic/
│    ├── README.md      // 취약점 개념 정리, 바이너리 분석, 익스플로잇
│    ├── vuln.c         // 취약점 포함 C소스코드
│    ├── build.sh       // vuln.c 컴파일
│    ├── exploit.py     // 익스플로잇 파이썬 코드
│    └── fix.c          // 취약점 제거한 C소스코드
...
└── images/             // .md 파일에 사용할 이미지 모음
```

---

## 사용법

### `setup.sh`

- 실습에 필요한 패키지, 툴, 32bit 환경 설치
- 최소권한, 패스워드 없는 사용자 baby 생성 -> 권한 상승 실습 시 사용
- 사용 : `sudo bash setup.sh`

### `(취약점 디렉터리)/build.sh`

- 실습용 디렉터리 `/tmp/(취약점 디렉터리)` 생성
- 실습용 디렉터리에 vuln.c 복사, vuln.c 컴파일, 권한 설정
- 사용 : `sudo bash build.sh`
- 이후 해당 디렉터리로 이동, 필요 시 계정 변경 후 실습
