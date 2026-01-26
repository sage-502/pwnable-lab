# bof-ret2libc-epilogue

## 1. 개요

이 디렉터리는 **ASLR OFF 환경에서 Buffer Overflow + ret2libc**를 시도하던 중,
`main` 함수의 **기대했던 형태와 다른 프롤로그/에필로그**로 인해
**단순한 saved RET overwrite가 성립하지 않았던 실습**에 대한 기록이다.

일반적인 ret2libc 예제와 달리,
이 바이너리는 `leave; ret` 형태가 아닌 epilogue를 사용하고 있어
단순히 offset 만큼의 임의의 padding을 사용할 경우 exploit이 실패한다.

본 실습의 목적은 다음과 같다.

* 단순한 ret2libc 실패 원인 분석
* main epilogue 구조 해석
* epilogue를 고려한 스택 재설계
* 최종적으로 ret2libc가 왜/어떻게 성공했는지 이해

---

## 2. 환경

* Architecture: x86 (32-bit)
* ASLR: OFF
* NX: ON
* PIE: OFF
* Stack Canary: OFF
* Compiler: gcc (`-O0`, 기본 main 사용)

---

## 3. 취약 코드

```c
// filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    setregid(getegid(), getegid());
    char buf[20];

    puts("input:");
    gets(buf);          // Buffer Overflow
    printf("%s\n", buf);

    return 0;
}
```

* `gets(buf)`로 인해 버퍼 오버플로우 발생 가능
* ASLR OFF 환경에서는 ret2libc가 가능할 것으로 예상했으나, 실제로는 단순한 saved RET overwrite가 실패함

---

## 4. 예상과 달랐던 점

일반적인 x86 함수라면 epilogue는 다음과 같을 것으로 기대했다.

```asm
leave
ret
```

이 경우:

* `[ebp+4]` = saved return address
* `buf`부터 overflow하면 RET을 바로 덮을 수 있다

하지만 실제 `main`의 프롤로그/에필로그는 다음과 같았다.

---

## 5. main 함수의 프롤로그 / 에필로그 분석

### 5.1 프롤로그

```asm
lea ecx,[esp+0x4]
and esp,0xfffffff0
push DWORD PTR [ecx-0x4]
push ebp
mov ebp,esp
push esi
push ebx
push ecx
sub esp,0x2c
```

특징:

* 스택 16바이트 정렬을 위해 `and esp, 0xfffffff0` 사용
* 정렬 과정에서 사라질 값을 보존하기 위해 `push [ecx-0x4]` 수행
* `ecx`, `ebx`, `esi` 레지스터를 스택에 저장



### 5.2 에필로그

```asm
lea esp,[ebp-0xc]
pop ecx
pop ebx
pop esi
pop ebp
lea esp,[ecx-0x4]
ret
```

핵심 포인트:

* `leave`가 아니라 **직접 esp를 복구**
* `ret` 직전에 `esp = ecx - 4`
* 즉, **RET이 읽히는 위치는 `[ecx-4]`**


스택 다이어그램: 

```
[높은주소]
+--------------+
│   [ecx-0x4]  │ saved ret 로 사용됨
+--------------+ [ebp+0x4]
│  saved ebp   │ 
+--------------+ [ebp]
│      esi     │ 
+--------------+ [ebp-0x4]
│      ebx     │ 
+--------------+ [ebp-0x8]
│      ecx     │ 
+--------------+ [ebp-0xc]
│      ...     │ 
+--------------+ 
│      buf     │ 
+--------------+ [ebp-0x2c]
[낮은주소]
```
※ 이 바이너리에서는 ret이 [ebp+4]가 아니라 ecx-4 위치를 참조한다.

---

## 6. 왜 단순 ret2libc가 실패했는가

초기 시도에서는 다음과 같이 payload를 구성했다.

```
"A" * offset
+ system
+ exit
+ "/bin/sh"
```

하지만 이 방식은 실패했다.

이유는:

* BOF로 인해 `[ebp-0xc]`에 저장된 **saved ecx**가 `0x41414141`로 덮임
* epilogue에서:

  ```asm
  pop ecx        ; ecx = 0x41414141
  lea esp,[ecx-0x4]
  ```
* 결과적으로:

  ```
  esp = 0x4141413d
  ```
* `ret` 수행 시 잘못된 주소 접근 → SIGSEGV

즉, 문제는 **RET이 아니라 epilogue의 스택 복구 과정**이었다.

---

## 7. 해결

이 바이너리에서는 다음 두 가지가 필요했다.

1. epilogue에서 복구되는 레지스터(`ecx`, `ebx`, `esi`)를 깨뜨리지 않기
2. `ret`이 참조하는 실제 위치인 **`[ecx-4]`에 ret2libc 체인을 배치하기**

### 핵심 아이디어

* BOF로 스택을 덮되,

  * `[ebp-0xc]` → 원래 ecx 값
  * `[ebp-0x8]` → 원래 ebx 값
  * `[ebp-0x4]` → 원래 esi 값
    
* epilogue가 정상 동작하도록 복구
* `ecx-4` 위치에:

  ```
  system
  exit
  "/bin/sh"
  ```

  순서로 체인 배치


### 기대했던 형태와 다른 프롤로그 직후 상태

아래는 `main` 함수의 프롤로그가 끝난 직후의 상태이다.

![prologue](https://github.com/sage-502/pwnable-lab/blob/main/images/bof-ret2libc-epilogue/01.png)

일반적인 `push ebp; mov ebp, esp` 형태와 달리,
이 바이너리는 스택 정렬과 레지스터 보존을 위해
`ecx`, `ebx`, `esi`를 스택에 저장하고 있다.

이 시점에서 이미 단순한 saved RET overwrite가 성립하지 않을 가능성이 있음을 알 수 있다.
(그러나 나는 늦게 깨달음)

### epilogue 이후 ret 직전 스택 상태

아래는 `main`의 epilogue를 모두 통과한 뒤,
`ret` 직전에 중단한 상태이다.

`lea esp, [ecx-0x4]`에 의해
실제로 `ret`이 참조하는 위치에
ret2libc 체인이 배치되어 있음을 확인할 수 있다.

![epilogue](https://github.com/sage-502/pwnable-lab/blob/main/images/bof-ret2libc-epilogue/02.png)

`ret` 직전 스택 상태:

```
ESP →
[ system address ]
[ exit address   ]
[ "/bin/sh"      ]
```

실행 흐름:

* `ret` → `__libc_system`
* `system("/bin/sh")` 실행 확인
* gdb에서 `EIP == __libc_system` 확인

`/bin/sh`가 non-interactive 환경에서는 바로 종료되지만,
이는 exploit 실패가 아니라 **입출력 환경 문제**이다.

※ gdb 환경에서 캡처한 스택/레지스터 값이며, 실제 실행 환경에서는 주소 값이 달라질 수 있다.

---

## 8. 여담

이 실습을 통해 알게 된 점은 다음과 같다.

* **saved RET = 항상 `[ebp+4]`가 아니다**
* ret2libc 실패 시:

  * payload만 보지 말고
  * **프롤로그/에필로그를 확인해야 한다**
* 컴파일러가 생성한 epilogue는 control flow에 직접적인 영향을 줄 수 있다
* 실습용으로는:

  * `vuln()` 함수 분리
  * `-fno-omit-frame-pointer`
  
  와 같이 교과서적인 스택 구조가 더 적합할 것 같다.
