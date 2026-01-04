# Format String Vulnerability

## 1. Format String Vulnerability 개요

### 정의

**Format String Vulnerability**는 `printf`, `fprintf`, `sprintf` 등 포맷 함수에 **사용자 입력을 그대로 포맷 문자열로 전달할 때** 발생한다.

```c
printf(buf);        // vulnerable
printf("%s", buf);  // safe
```

### 왜 취약한가?

- `printf`는 포맷 문자열을 **명령처럼 해석**
- `%x`, `%p`, `%s`, `%n` 등을 만나면 **가변 인자(varargs)** 를 읽으려고 시도
- 실제로는 인자를 전달하지 않았기 때문에 → **스택의 다른 값들을 인자로 착각하고 읽거나 씀**

### 결과적으로 가능한 공격

1. 스택 / libc / 바이너리 주소 leak
2. 임의 메모리 쓰기 (`%n`)
3. GOT overwrite → RCE

---

## 2. printf 동작 방식 (32-bit, cdecl)

### 인자 전달 구조

```c
printf(fmt, arg1, arg2, arg3, ...);
```

32bit cdecl 기준 스택 구조:

```
낮은 주소
[ebp+0]   : saved ebp
[ebp+4]   : return address
[ebp+8]   : fmt
[ebp+12]  : arg1
[ebp+16]  : arg2
[ebp+20]  : arg3
...
높은 주소
```

> **노트**
> - `%x` 하나당 4바이트 (32bit 기준)
> - `printf`는 인자의 유효성을 검사하지 않고, fmt 이후 스택 영역을 가변 인자로 가정해 순차적으로 읽는다.

---

### 취약한 호출의 실제 의미

```c
printf(buf);
```

- 전달된 인자는 오직 `fmt = &buf` 하나
- `%x` 등장 시:
  - "다음 인자"가 없는데도
  - 스택에서 계속 4바이트씩 읽음

그 결과:
- return address
- libc 주소
- main의 지역 변수
- **main의 buf 내용**

까지 인자처럼 읽혀 출력됨

> **노트**
> - printf가 `buf`를 인자로 받는 것이 아니라
> - printf가 **없는 가변 인자를 읽다가**, 스택에 있던 **main의 buf 영역까지 읽게 된 것**

---

## 3. Leak과 Offset 계산

### Leak 원리

```bash
AAAA.%x.%x.%x.%x.%x.%x
```

- `%x` → “다음 인자 출력”
- 실제로는 스택의 값들이 순서대로 출력됨

출력 예:

```
AAAA.64.f7fa65c0.804918d.f7ffdb8c.1.41414141
```

- `0xf7xxxxxx` → libc
- `0x0804xxxx` → binary
- `0xffffxxxx` → stack
- `0x41414141` → 입력한 `AAAA`

> **노트**
> (관례 상) 32bit Linux 환경에서
> - `0x0804xxxx` 대역은 main binary,
> - `0xf7xxxxxx` 대역은 libc 등 shared library,
> - `0xffffxxxx` 대역은 stack 영역에 매핑되는 경우가 많다.


### Offset 계산 방법

1. 마커 삽입

```bash
AAAA.%x.%x.%x.%x.%x.%x
```

2. 출력에서 `41414141` 위치 확인

3. 결론

```
offset = 6
```

의미: “printf가 6번째로 읽은 인자 슬롯에 main의 buf 내용(AAAA)이 있었다”

> **노트**
> Offset의 의미 : printf가 가변 인자라고 착각하고 읽는 값들 중 내가 원하는 값이 몇 번째로 읽히는지 나타내는 것.

---

## 바이너리 분석
(추가 예정)
> 예제 코드로 leak, offset 연산 실습 결과 정리
